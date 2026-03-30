# 🥗 NutriAgent — AI Nutrition Assistant with Persistent Memory

> **Educational project** — companion code for the lesson  
> *"Build a Nutrition Agent That Never Forgets"*  
> on [future-with-ai.com/academy/agents/cognee](https://future-with-ai.com/academy/agents/cognee)

**✨ Features:**
- 🧠 Persistent memory across sessions (Cognee knowledge graph)
- 💬 Beautiful web chat UI (React + TailwindCSS)
- 🔄 3-node LangGraph workflow (recall → respond → remember)
- 🚀 FastAPI backend with REST API + WebSocket support
- 📚 Comprehensive documentation for students

---

## What This Project Builds

A personalized AI nutrition assistant that **remembers users across sessions**.

Most chatbots reset when you close the window. NutriAgent stores every user's
dietary restrictions, health goals, calorie targets, and meal history in a
persistent knowledge graph (powered by Cognee). The next time a user connects,
the agent already knows everything — no repeated introductions required.

```
Session 1
You:         What can I eat for breakfast?
NutriAgent:  Good morning, Sarah! Since you're vegetarian and avoiding
             peanuts, here are options for your 1,800 kcal goal: ...

Session 2  (new process, same memory)
You:         I had overnight oats. Also avoiding dairy this week.
NutriAgent:  Got it — I've noted you're dairy-free this week and had
             oats for breakfast (~420 kcal). I'll remember this going forward!
```

The key insight: **standard RAG stores chunks. Cognee stores relationships.**  
The agent can answer *"what should I avoid given everything I've told you?"*
without the user repeating themselves every session.

---

## Tech Stack

| Component | Library | Role |
|---|---|---|
| Memory Layer | `cognee` | Knowledge graph + vector search for persistent user memory |
| Agent Orchestration | `langgraph` | Typed state graph with read → respond → write loop |
| LLM Client | `langchain-openai` | OpenAI-compatible client pointed at DeepSeek |
| LLM Provider | DeepSeek (`deepseek-chat`) | Cheap, capable LLM (~$0.14 / M tokens) |
| Web Server | `fastapi` + `uvicorn` | REST API + WebSocket chat interface |
| Frontend | React + TailwindCSS | Modern chat UI (single-page app) |
| Config | `python-dotenv` | API key management via `.env` |
| Runtime | Python 3.10+ | Async throughout (`asyncio`) |

---

## Architecture

```
User Input
    │
    ▼
LangGraph Agent ──────────────────────► DeepSeek API
    │   ▲                                   │
    │   │ memory_context                    │ response
    ▼   │                                   │
Cognee Memory ◄────────────────────────────┘
  ├── Vector Search  (semantic similarity)
  └── Knowledge Graph (relational entity links)
       │
       ├── user_{id}         ← static profile (goals, restrictions)
       └── user_{id}_meals   ← timestamped meal log + new facts
```

### The 3-Node LangGraph Workflow

```
[START] → recall → respond → remember → [END]
```

| Node | What it does |
|---|---|
| `recall` | Searches Cognee (vector + graph) and fills `memory_context` in the shared state |
| `respond` | Injects `memory_context` into the system prompt, calls DeepSeek, stores the reply |
| `remember` | Asks the LLM to extract NEW facts; writes them to Cognee if found |

---

## Project Structure

```
nutrition-agent/
├── .env.example      ← template for your API keys (copy → .env)
├── .gitignore        ← excludes .env, venv/, .cognee_system/
├── requirements.txt  ← dependencies (agent core + web server)
├── memory.py         ← Cognee memory manager (all reads + writes)
├── agent.py          ← LangGraph agent: state + 3 nodes + build_agent()
├── main.py           ← CLI entry point: profile setup + interactive chat loop
├── app.py            ← FastAPI web server with REST API + WebSocket
├── run_web.bat       ← convenience script to start web server
└── static/
    └── index.html    ← React chat UI (single-page app)
```

Each file has **one responsibility** (Single Responsibility Principle):

- `memory.py` knows about Cognee and nothing else.
- `agent.py` knows about LangGraph and imports only the two memory functions it needs.
- `main.py` wires them together for CLI usage.
- `app.py` exposes the agent via HTTP for web UI access.
- `static/index.html` is the complete frontend (React + TailwindCSS via CDN).

---

## Setup

### 1 — Clone & enter the project

```bash
git clone https://github.com/your-username/nutrition-agent.git
cd nutrition-agent
```

### 2 — Create a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Configure your API key

Copy the example env file and fill in your DeepSeek key:

```bash
cp .env.example .env
```

Edit `.env`:

```env
DEEPSEEK_API_KEY=sk-your-real-key-here
LLM_API_KEY=sk-your-real-key-here
LLM_PROVIDER=openai
LLM_MODEL=deepseek-chat
LLM_ENDPOINT=https://api.deepseek.com/v1
```

Get a DeepSeek key at [platform.deepseek.com](https://platform.deepseek.com).

> **DeepSeek is OpenAI-compatible.** Both Cognee and LangChain accept any
> OpenAI-compatible endpoint — just override `base_url` / `openai_api_base`.
> No custom SDK required.

### 5 — Run the application

You can run NutriAgent in two modes:

#### Option A: Web UI (Recommended for Students)

Start the web server with the modern chat interface:

```bash
# Windows
run_web.bat

# Or manually
venv\Scripts\python.exe app.py
```

Then open your browser to **http://localhost:8000**

You'll see a beautiful onboarding form where you can:
- Enter your name and nutrition goals
- Set dietary restrictions (vegetarian, vegan, gluten-free, etc.)
- Specify allergies
- Define health goals

After onboarding, you get a persistent chat interface that remembers everything across sessions.

**API Documentation:** Visit http://localhost:8000/docs for interactive API docs (Swagger UI)

#### Option B: Command-Line Interface

Run the terminal-based chat:

```bash
venv\Scripts\python.exe main.py
```

Expected output:

```
⏳ Setting up user profile in Cognee (first run may take 5–15 s)…
✅ Profile stored.

🥗 NutriAgent ready. Type 'quit' to exit.

You: What can I eat for breakfast?

🤖 NutriAgent: Good morning, Sarah! Since you're vegetarian and avoiding
peanuts, here are some options for your 1,800 kcal goal: ...
```

> **First run note:** `cognify()` sends the profile text to DeepSeek for entity
> extraction and graph building. This takes **5–15 seconds**. Subsequent
> searches are fast (< 1 s).

---

## How the Code Works — File by File

### `memory.py` — Cognee Memory Manager

The entire Cognee interface lives here. Three public async functions:

| Function | What it does |
|---|---|
| `store_user_profile(user_id, profile)` | Converts a profile dict to natural-language text, stages it with `cognee.add()`, then calls `cognee.cognify()` to build the knowledge graph |
| `store_meal_memory(user_id, meal, details)` | Appends a timestamped meal/fact entry to the user's meal dataset |
| `recall_user_context(user_id, query)` | Searches both datasets with Cognee's hybrid search, returns top 5 results as a string |

**Why two datasets per user?**  
`user_{id}` holds the static profile. `user_{id}_meals` holds the growing log.
Separating them avoids cross-contamination during search and lets you query
meal history independently of profile data.

**Why plain text instead of JSON for profiles?**  
Cognee's ECL pipeline (Extract → Cognify → Load) feeds the text to the LLM for
entity extraction. Natural language ("Daily calorie goal: 1800 kcal") produces
richer entity relationships than raw JSON keys.

---

### `agent.py` — LangGraph Nutrition Agent

Defines `AgentState` (a `TypedDict`) and three async node functions. The state
dict flows through every node — each node reads from it, adds/updates a field,
and returns the updated state. Nodes are pure functions with no shared global
state.

```python
class AgentState(TypedDict):
    user_id: str          # whose Cognee datasets to use
    user_message: str     # raw user input this turn
    memory_context: str   # filled by recall; injected into prompt
    response: str         # filled by respond; printed to the user
```

`build_agent()` assembles and compiles the graph:

```python
graph = StateGraph(AgentState)
graph.add_node("recall", recall)
graph.add_node("respond", respond)
graph.add_node("remember", remember)
graph.set_entry_point("recall")
graph.add_edge("recall", "respond")
graph.add_edge("respond", "remember")
graph.add_edge("remember", END)
return graph.compile()
```

---

### `main.py` — Entry Point

1. Builds the agent via `build_agent()`.
2. Stores the demo profile (`store_user_profile`) — simulates first-time onboarding.
3. Runs an infinite `while True` loop: reads input → invokes agent → prints response.

All four state keys must be present when calling `agent.ainvoke()`.
`memory_context` and `response` start as empty strings and are filled by the graph.

---

## Extension Ideas

These are documented for future contributors:

1. **REST API** — Wrap `agent.ainvoke()` in a FastAPI `POST /chat` endpoint.
   Pass `user_id` from the auth header, message from the request body.
   This makes the agent HTTP-accessible and multi-user in ~20 extra lines.

2. **Recipe database** — Ingest 500 recipes into Cognee:
   `cognee.add(recipe_text, dataset_name="recipes")`.
   The agent can then recommend specific dishes by name from persistent memory.

3. **Meal photo input** — Cognee supports image ingestion.
   Accept a base64 image, call `cognee.add(image, dataset_name=f"user_{user_id}_meals")`.
   Use a vision-capable model to extract nutritional data automatically.

4. **Weekly summary** — Schedule a weekly call to
   `cognee.search("meals eaten this week", datasets=[...])` and generate a
   personalised nutrition report.

5. **Local model** — Replace DeepSeek with Ollama:
   `openai_api_base="http://localhost:11434/v1"`, `model="llama3.1:8b"`.
   No API costs, fully offline operation.

6. **Skip re-onboarding** — Before calling `store_user_profile()`, check if
   the user dataset already exists in Cognee. If it does, skip setup and go
   straight to the chat loop. This is the production pattern.

---

## Common Issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `TimeoutError: LLM connection test timed out` | Network/firewall blocking DeepSeek API, or invalid API key | 1. Verify your API key at [platform.deepseek.com](https://platform.deepseek.com)<br>2. Check firewall/proxy settings<br>3. Add `COGNEE_SKIP_CONNECTION_TEST=true` to `.env` to bypass the test |
| `cognify()` hangs forever | Bad API key or no internet | Check `DEEPSEEK_API_KEY` in `.env` |
| `recall` returns empty context | Profile not yet cognified | Wait for `store_user_profile()` to finish on first run |
| `ImportError: langchain_openai` | Dependency not installed | Activate venv first: `venv\Scripts\activate`, then `pip install -r requirements.txt` |
| `ModuleNotFoundError` when running | Virtual environment not activated | Use `venv\Scripts\python.exe main.py` or activate venv first |
| Agent doesn't remember across runs | `.cognee_system/` deleted | Don't delete this folder — it's the persistent store |

---

## License

MIT — free to use, modify, and share for educational and commercial purposes.

---

*Companion code for the [future-with-ai.com Academy](https://future-with-ai.com/academy/agents/cognee) lesson.*
