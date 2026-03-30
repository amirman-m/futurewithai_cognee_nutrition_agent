"""
agent.py — LangGraph Nutrition Agent
======================================
Single responsibility: define the agent state, the three processing nodes,
and the compiled LangGraph workflow. No direct Cognee calls live here —
all memory operations are delegated to memory.py.

Workflow (read → reason → write):
    [START] → recall → respond → remember → [END]

    recall   : fetch relevant user context from Cognee before generation.
    respond  : inject context into system prompt, call DeepSeek, produce reply.
    remember : extract new facts from this turn, persist them back to Cognee.

Why LangGraph instead of a plain async function?
  - Each node is a pure function: easy to test in isolation.
  - Built-in tracing and checkpointing come for free.
  - Conditional branching (e.g. route to a specialist node on medical keywords)
    is a one-line addition to the graph later.
  - The typed AgentState dict makes data flow between nodes explicit and safe.
"""

import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from memory import (
    clear_pending_memory,
    confirm_pending_memory,
    get_pending_memory,
    recall_user_context,
    set_pending_memory,
)

# ── Environment ───────────────────────────────────────────────────────────────

load_dotenv()

# ── LLM Client ────────────────────────────────────────────────────────────────
# ChatOpenAI works with any OpenAI-compatible endpoint.
# We override openai_api_base to point at DeepSeek — no custom SDK needed.
# temperature=0.7 balances creativity with factual accuracy for nutrition advice.

configured_model = os.getenv("LLM_MODEL", "deepseek-chat")
chat_model = configured_model.split("/", 1)[1] if "/" in configured_model else configured_model

llm = ChatOpenAI(
    model=chat_model,
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base=os.getenv("LLM_ENDPOINT", "https://api.deepseek.com/v1"),
    temperature=0.7,
)


# ── Agent State ───────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    """
    Shared data container that flows through every node in the graph.

    Each node receives the full state dict, may update specific keys,
    and returns the updated state. Nodes never share global mutable state.

    Fields:
        user_id:        Identifies whose Cognee datasets to read/write.
        user_message:   The raw input from the user this turn.
        memory_context: Filled by the recall node; injected into the prompt.
        response:       Filled by the respond node; printed to the user.
    """

    user_id: str
    user_message: str
    memory_context: str
    response: str
    pending_memory_action: str


# ── Node 1: recall ────────────────────────────────────────────────────────────

async def recall(state: AgentState) -> AgentState:
    """
    Node 1 — retrieve relevant memory before generation.

    Calls Cognee's hybrid search (vector + graph) across both the user's
    profile dataset and their meal-history dataset. The top 5 results are
    stored in memory_context so the next node can inject them into the prompt.

    This runs BEFORE the LLM call so the model always has full context.
    """
    context = await recall_user_context(state["user_id"], state["user_message"])
    return {**state, "memory_context": context, "pending_memory_action": "none"}


def _is_confirmation(message: str) -> str | None:
    normalized = message.strip().lower()

    if normalized in {"yes", "y", "sure", "ok", "okay", "please do", "remember it", "save it"}:
        return "confirm"

    if normalized in {"no", "n", "nope", "don't", "do not", "cancel", "not now"}:
        return "reject"

    return None


async def _detect_memory_candidate(user_message: str, assistant_response: str) -> dict | None:
    detection_prompt = (
        f'User message: "{user_message}"\n'
        f'Assistant response: "{assistant_response}"\n\n'
        "Decide whether the user revealed a stable fact worth remembering for future nutrition support.\n"
        "Only consider important facts such as:\n"
        "- dietary preferences or dislikes\n"
        "- allergies or intolerances\n"
        "- restrictions or foods/diets the user does not want again\n"
        "- health goal changes\n"
        "- critical instructions for future recommendations\n"
        "- meaningful meal history worth saving\n\n"
        "If there is nothing important to store, return exactly: none\n\n"
        "Otherwise return valid JSON with this exact shape:\n"
        '{"type":"preference|restriction|allergy|goal|meal_memory|critical_instruction","summary":"short summary","details":"short factual description","question":"short confirmation question for the user"}'
    )

    result = await llm.ainvoke([HumanMessage(content=detection_prompt)])
    content = result.content.strip()

    if content.lower() == "none":
        return None

    import json

    try:
        candidate = json.loads(content)
    except json.JSONDecodeError:
        return None

    required_keys = {"type", "summary", "details", "question"}
    if not required_keys.issubset(candidate):
        return None

    return candidate


# ── Node 2: respond ───────────────────────────────────────────────────────────

async def respond(state: AgentState) -> AgentState:
    """
    Node 2 — generate a personalized response using retrieved memory.

    Builds a system prompt that presents the Cognee-retrieved context clearly,
    then calls DeepSeek with the system prompt + the user's message.

    The system prompt instructs the LLM to:
      - Stay in the role of a personalized nutrition assistant.
      - Use the retrieved context (not hallucinate user details).
      - Acknowledge when it learns or remembers new information.
      - Keep answers concise, warm, and actionable.
    """
    pending_memory = get_pending_memory(state["user_id"])
    confirmation = _is_confirmation(state["user_message"])

    if pending_memory and confirmation == "confirm":
        confirmed_memory = confirm_pending_memory(state["user_id"])
        summary = confirmed_memory.get("summary", "that") if confirmed_memory else "that"
        return {
            **state,
            "response": f"Got it — I’ll remember {summary} for future recommendations.",
            "pending_memory_action": "confirmed",
        }

    if pending_memory and confirmation == "reject":
        clear_pending_memory(state["user_id"])
        return {
            **state,
            "response": "Understood — I won’t save that to memory.",
            "pending_memory_action": "rejected",
        }

    if pending_memory:
        return {
            **state,
            "response": f"Before we continue: {pending_memory.get('question', 'Should I remember that for later?')} Please answer yes or no.",
            "pending_memory_action": "awaiting_confirmation",
        }

    system_prompt = (
        "You are a personalized nutrition assistant with persistent memory.\n\n"
        "Here is everything you currently know about this user:\n"
        f"{state['memory_context']}\n\n"
        "Instructions:\n"
        "- Use the context above to give highly personalized, specific advice.\n"
        "- If the user mentions new dietary changes, goals, dislikes, or critical preferences, be helpful now but do not claim they are already saved.\n"
        "- If no prior context exists, ask a warm onboarding question.\n"
        "- Keep responses concise, warm, and practical."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["user_message"]),
    ]

    llm_response = await llm.ainvoke(messages)
    return {**state, "response": llm_response.content, "pending_memory_action": "none"}


# ── Node 3: remember ──────────────────────────────────────────────────────────

async def remember(state: AgentState) -> AgentState:
    """
    Node 3 — extract new facts and write them back to Cognee.

    Asks the LLM to look at BOTH sides of this conversation turn and identify
    any NEW information worth persisting (new restriction, updated goal, meal
    just logged, etc.). If new facts exist, they are written to the user's
    meal/facts dataset so they survive across sessions.

    If the LLM responds with "nothing new", no write is performed — this
    prevents polluting the graph with noise on routine exchanges.

    Returns the state unchanged (memory write is a side effect).
    """
    if state.get("pending_memory_action") != "none":
        return state

    candidate = await _detect_memory_candidate(state["user_message"], state["response"])
    if candidate:
        set_pending_memory(
            state["user_id"],
            {
                "type": candidate["type"],
                "summary": candidate["summary"],
                "details": candidate["details"],
                "question": candidate["question"],
                "created_at": state.get("user_message", ""),
            },
        )
        return {
            **state,
            "response": (
                f"{state['response']}\n\n"
                f"Before I save this for future recommendations: {candidate['question']}"
                " Please answer yes or no."
            ),
            "pending_memory_action": "awaiting_confirmation",
        }

    return state  # state is returned unchanged; write was a side effect


# ── Graph Assembly ────────────────────────────────────────────────────────────

def build_agent():
    """
    Assemble and compile the three-node LangGraph workflow.

    Graph topology:
        recall → respond → remember → END

    Returns:
        A compiled LangGraph runnable. Call .ainvoke(state_dict) to run it.
    """
    graph = StateGraph(AgentState)

    # Register the three nodes with human-readable names.
    graph.add_node("recall", recall)
    graph.add_node("respond", respond)
    graph.add_node("remember", remember)

    # Set the entry point (first node to execute).
    graph.set_entry_point("recall")

    # Linear edges: each node passes control to the next.
    graph.add_edge("recall", "respond")
    graph.add_edge("respond", "remember")
    graph.add_edge("remember", END)

    return graph.compile()
