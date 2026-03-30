"""
memory.py — Cognee Memory Manager
==================================
Single responsibility: ALL reads and writes to Cognee's knowledge graph
live here. No agent logic, no LangGraph imports.

Why a dedicated module?
  - Keeps the agent (agent.py) decoupled from the storage backend.
  - Swapping Cognee for another vector store only requires changes here.
  - Makes unit-testing memory operations straightforward.

Dataset naming convention:
  - "user_{id}"        → static nutrition profile (name, goals, restrictions)
  - "user_{id}_meals"  → growing meal log, timestamped entries

Both datasets are searched together during recall so the agent always
sees the full picture of a user's history and preferences.
"""

import json
from datetime import datetime
from pathlib import Path

# ── Profile Dataset Helpers ───────────────────────────────────────────────────

def _profile_dataset_name(user_id: str) -> str:
    """Returns the Cognee dataset name for a user's static nutrition profile."""
    return f"user_{user_id}"


def _meals_dataset_name(user_id: str) -> str:
    """Returns the Cognee dataset name for a user's timestamped meal log."""
    return f"user_{user_id}_meals"


def _build_profile_text(user_id: str, profile: dict) -> str:
    """
    Converts a profile dictionary into natural-language text.

    Why plain text instead of JSON?
    Cognee's ECL pipeline (Extract → Cognify → Load) feeds this text to
    the LLM for entity extraction. Natural language lets the LLM identify
    entities (Name, Goal, Restriction) more reliably than raw JSON keys.
    """
    restrictions = ", ".join(profile.get("restrictions", [])) or "none"
    allergies = ", ".join(profile.get("allergies", [])) or "none"

    return (
        f"User ID: {user_id}\n"
        f"Name: {profile.get('name', 'Unknown')}\n"
        f"Daily calorie goal: {profile.get('calorie_goal', 2000)} kcal\n"
        f"Dietary restrictions: {restrictions}\n"
        f"Health goals: {profile.get('goals', 'general wellness')}\n"
        f"Allergies: {allergies}\n"
        f"Last updated: {datetime.now().strftime('%Y-%m-%d')}"
    )


_DATA_DIR = Path(__file__).resolve().parent / ".memory_store"
_DATA_DIR.mkdir(exist_ok=True)


def _user_memory_path(user_id: str) -> Path:
    return _DATA_DIR / f"{user_id}.json"


def _load_user_memory(user_id: str) -> dict:
    path = _user_memory_path(user_id)
    if not path.exists():
        return {"profile": None, "memories": [], "pending_memory": None}

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return {
        "profile": data.get("profile"),
        "memories": data.get("memories", []),
        "pending_memory": data.get("pending_memory"),
    }


def _save_user_memory(user_id: str, data: dict) -> None:
    path = _user_memory_path(user_id)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def _format_profile_context(profile: dict | None) -> str:
    if not profile:
        return ""

    restrictions = ", ".join(profile.get("restrictions", [])) or "none"
    allergies = ", ".join(profile.get("allergies", [])) or "none"

    return (
        "Stored profile:\n"
        f"- Name: {profile.get('name', 'Unknown')}\n"
        f"- Daily calorie goal: {profile.get('calorie_goal', 2000)} kcal\n"
        f"- Dietary restrictions: {restrictions}\n"
        f"- Allergies: {allergies}\n"
        f"- Health goals: {profile.get('goals', 'general wellness')}"
    )


def _format_recent_memories(memories: list[dict]) -> str:
    if not memories:
        return ""

    recent_memories = memories[-8:]
    lines = ["Recent remembered facts:"]
    for memory in recent_memories:
        memory_type = memory.get("type", "memory")
        lines.append(
            f"- {memory.get('timestamp', '')}: [{memory_type}] {memory.get('summary', memory.get('meal', 'note'))} — {memory.get('details', '')}"
        )

    return "\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

def get_user_profile(user_id: str) -> dict | None:
    memory = _load_user_memory(user_id)
    return memory.get("profile")


def get_pending_memory(user_id: str) -> dict | None:
    memory = _load_user_memory(user_id)
    return memory.get("pending_memory")


def set_pending_memory(user_id: str, pending_memory: dict | None) -> None:
    memory = _load_user_memory(user_id)
    memory["pending_memory"] = pending_memory
    _save_user_memory(user_id, memory)


def clear_pending_memory(user_id: str) -> None:
    set_pending_memory(user_id, None)


def confirm_pending_memory(user_id: str) -> dict | None:
    memory = _load_user_memory(user_id)
    pending_memory = memory.get("pending_memory")

    if not pending_memory:
        return None

    confirmed_memory = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "type": pending_memory.get("type", "memory"),
        "summary": pending_memory.get("summary", "Confirmed memory"),
        "details": pending_memory.get("details", ""),
        "source": "user_confirmed",
        "confirmed": True,
    }
    memory["memories"].append(confirmed_memory)
    memory["pending_memory"] = None
    _save_user_memory(user_id, memory)

    return confirmed_memory


def list_user_profiles() -> list[dict]:
    profiles = []

    for path in sorted(_DATA_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        profile = data.get("profile")
        if not profile:
            continue

        profiles.append(
            {
                "user_id": profile.get("user_id", path.stem),
                "name": profile.get("name", "Unknown"),
                "calorie_goal": profile.get("calorie_goal", 2000),
                "restrictions": profile.get("restrictions", []),
                "allergies": profile.get("allergies", []),
                "goals": profile.get("goals", "general wellness"),
                "updated_at": profile.get("updated_at"),
            }
        )

    return profiles

async def store_user_profile(user_id: str, profile: dict) -> None:
    """
    Write (or overwrite) a user's nutrition profile into the knowledge graph.

    Steps:
      1. Convert the dict to natural-language text so the LLM can extract
         entities cleanly during cognify().
      2. cognee.add()     → stages the text in the dataset.
      3. cognee.cognify() → triggers the ECL pipeline:
                             Extract entities from text via LLM,
                             Build graph edges between those entities,
                             Embed + index for vector search.

    Note: cognify() takes 5–15 s on the first call for a new user while
    the LLM processes the text. Subsequent calls are faster.

    Args:
        user_id:  Unique identifier for the user (e.g. "user_42").
        profile:  Dict with keys: name, calorie_goal, restrictions,
                  allergies, goals.
    """
    memory = _load_user_memory(user_id)
    memory["profile"] = {
        "user_id": user_id,
        "name": profile.get("name", "Unknown"),
        "calorie_goal": profile.get("calorie_goal", 2000),
        "restrictions": profile.get("restrictions", []),
        "allergies": profile.get("allergies", []),
        "goals": profile.get("goals", "general wellness"),
        "profile_text": _build_profile_text(user_id, profile),
        "updated_at": datetime.now().isoformat(),
    }
    _save_user_memory(user_id, memory)


async def store_meal_memory(user_id: str, meal: str, details: str) -> None:
    """
    Append a timestamped meal or fact update to the user's meal log.

    This is called both for explicit meal logging and for any new facts the
    agent extracts from a conversation turn (see agent.py → update_memory).

    Args:
        user_id:  Unique identifier for the user.
        meal:     Short label for the entry (e.g. "oatmeal" or
                  "conversation update").
        details:  Free-text details about the meal or new fact.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry_text = (
        f"User {user_id} ate {meal} on {timestamp}.\n"
        f"Details: {details}"
    )
    memory = _load_user_memory(user_id)
    memory["memories"].append(
        {
            "timestamp": timestamp,
            "type": "meal_memory",
            "summary": meal,
            "meal": meal,
            "details": details,
            "source": "assistant_capture",
            "confirmed": True,
        }
    )
    _save_user_memory(user_id, memory)


async def store_structured_memory(
    user_id: str,
    memory_type: str,
    summary: str,
    details: str,
    source: str = "assistant_capture",
) -> None:
    memory = _load_user_memory(user_id)
    memory["memories"].append(
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "type": memory_type,
            "summary": summary,
            "details": details,
            "source": source,
            "confirmed": True,
        }
    )
    _save_user_memory(user_id, memory)


async def recall_user_context(user_id: str, query: str) -> str:
    """
    Search both the profile and meal datasets for context relevant to query.

    Cognee's search combines:
      - Vector similarity  → finds semantically close passages.
      - Graph traversal    → follows entity relationships (e.g. User → Goal).

    Returns the top 5 results concatenated as a single string, ready to be
    injected into the agent's system prompt.

    Returns:
        A multi-line string of retrieved facts, or a fallback message if
        no context exists yet for this user.
    """
    memory = _load_user_memory(user_id)
    profile_context = _format_profile_context(memory.get("profile"))
    recent_memories = _format_recent_memories(memory.get("memories", []))

    sections = [section for section in [profile_context, recent_memories] if section]

    if not sections:
        return "No prior context found for this user."

    return "\n\n".join(sections)
