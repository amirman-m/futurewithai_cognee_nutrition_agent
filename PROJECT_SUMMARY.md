# NutriAgent — Complete Project Summary

## 🎯 Project Overview

**NutriAgent** is a fully-functional AI nutrition assistant with persistent memory, built as an educational project to demonstrate production-grade AI agent architecture.

**Key Achievement:** Unlike standard chatbots that forget everything between sessions, NutriAgent remembers each user's dietary restrictions, health goals, and meal history indefinitely using Cognee's knowledge graph.

---

## 📦 What's Included

### Core Agent Files (CLI Version)
- **`memory.py`** (161 lines) — Cognee memory manager with 3 public async functions
- **`agent.py`** (186 lines) — LangGraph 3-node workflow (recall → respond → remember)
- **`main.py`** (91 lines) — CLI entry point with interactive chat loop

### Web Interface Files
- **`app.py`** (243 lines) — FastAPI server with REST API + WebSocket support
- **`static/index.html`** (500+ lines) — Complete React SPA with TailwindCSS
- **`run_web.bat`** — Convenience script to start web server

### Configuration & Documentation
- **`.env.example`** — Template for API keys (safe to commit)
- **`.gitignore`** — Protects secrets and build artifacts
- **`requirements.txt`** — 7 dependencies (agent core + web server)
- **`README.md`** — Full documentation (11KB)
- **`QUICKSTART.md`** — 5-minute setup guide
- **`WEB_UI_GUIDE.md`** — Deep dive into web architecture
- **`TROUBLESHOOTING.md`** — Common issues + solutions

---

## 🏗️ Architecture Highlights

### 1. Clean Separation of Concerns (SOLID Principles)

```
memory.py    → Knows ONLY about Cognee (storage layer)
agent.py     → Knows ONLY about LangGraph (orchestration layer)
main.py      → Wires them together for CLI usage
app.py       → Exposes agent via HTTP for web access
```

Each file has exactly one responsibility. Swapping Cognee for another vector store only requires changes to `memory.py`.

### 2. Three-Node LangGraph Workflow

```
[START] → recall → respond → remember → [END]
```

- **recall:** Searches Cognee (vector + graph) for relevant user context
- **respond:** Injects context into system prompt, calls DeepSeek LLM
- **remember:** Extracts new facts from conversation, writes back to Cognee

This read → reason → write loop is what makes the agent genuinely learn over time.

### 3. Persistent Memory via Cognee

Two datasets per user:
- `user_{id}` — static profile (name, goals, restrictions)
- `user_{id}_meals` — growing meal log + conversation updates

Cognee's ECL pipeline (Extract → Cognify → Load):
1. Sends text to LLM for entity extraction
2. Builds graph edges between entities
3. Stores vector embeddings for semantic search

Result: Both semantic similarity AND relational graph traversal work together.

### 4. Modern Web UI

- **Onboarding flow** — beautiful form for profile creation
- **Chat interface** — message bubbles, typing indicator, auto-scroll
- **Persistent sessions** — `localStorage` stores `user_id`, all data lives in Cognee
- **Zero build tools** — React + TailwindCSS via CDN (educational simplicity)

---

## 🎓 Educational Value

### What Students Learn

1. **Knowledge Graph Memory**
   - Why graphs > chunks for relational data
   - How Cognee combines vector search + graph traversal
   - Entity extraction via LLM prompting

2. **Agent Orchestration**
   - LangGraph's typed state pattern
   - Pure functions vs shared mutable state
   - Conditional branching in graphs (extensible)

3. **Async Python**
   - `async def` / `await` throughout
   - FastAPI's native async support
   - Non-blocking I/O for scalability

4. **REST API Design**
   - Request/response models with Pydantic
   - CORS middleware for frontend access
   - Automatic OpenAPI docs (Swagger UI)

5. **Clean Code Practices**
   - Single Responsibility Principle
   - Dependency injection (agent passed via `app.state`)
   - Environment variable management (`.env`)

---

## 🚀 Quick Start

```bash
# 1. Install
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Add your DeepSeek API key to .env

# 3. Run web UI
run_web.bat
# Open http://localhost:8000

# OR run CLI
python main.py
```

---

## 📊 Code Statistics

| Metric | Value |
|--------|-------|
| Total Python LOC | ~700 lines |
| Frontend LOC | ~500 lines (HTML + React) |
| Documentation | ~25KB across 4 markdown files |
| Dependencies | 7 (cognee, langgraph, langchain-openai, fastapi, uvicorn, pydantic, python-dotenv) |
| API Endpoints | 4 (chat, profile, health, websocket) |
| React Components | 4 (main app, onboarding, message, typing indicator) |

---

## 🔧 Technical Decisions Explained

### Why DeepSeek?
- OpenAI-compatible API (no custom SDK needed)
- Extremely cheap (~$0.14/M tokens vs GPT-4's $30/M)
- Good quality for nutrition advice

### Why Cognee over LangChain Memory?
- Persistent storage (survives process restarts)
- Knowledge graph (relational queries, not just similarity)
- Multi-user isolation (dataset-per-user pattern)

### Why LangGraph over plain async functions?
- Built-in tracing and checkpointing
- Easy to add conditional branching later
- Each node is testable in isolation

### Why FastAPI over Flask?
- Native async support (works with async agent)
- Automatic OpenAPI docs
- WebSocket support built-in
- Modern, type-safe request/response models

### Why React via CDN vs build tools?
- Educational simplicity (view-source works)
- Zero setup (no npm, webpack, babel config)
- Students can edit and refresh immediately

---

## 🎯 Extension Ideas for Students

### Beginner
1. Add more dietary restrictions to the onboarding form
2. Change the color scheme (edit TailwindCSS classes)
3. Add a "clear chat" button

### Intermediate
4. Implement meal logging endpoint (direct call to `store_meal_memory`)
5. Add calorie tracking (query Cognee for today's meals, sum calories)
6. Show user profile in the UI (read from Cognee on load)

### Advanced
7. Ingest recipe database into Cognee (500 recipes as a separate dataset)
8. Add meal photo upload (Cognee supports images)
9. Implement streaming responses via WebSocket
10. Add user authentication (replace random `user_id` with real login)
11. Deploy to production (Docker + nginx + HTTPS)

---

## 📁 File Manifest

```
nutrition-agent/
├── Core Agent
│   ├── memory.py              # Cognee interface (3 public functions)
│   ├── agent.py               # LangGraph workflow (3 nodes)
│   └── main.py                # CLI entry point
│
├── Web Interface
│   ├── app.py                 # FastAPI server
│   ├── static/index.html      # React SPA
│   └── run_web.bat            # Startup script
│
├── Configuration
│   ├── .env.example           # API key template
│   ├── .gitignore             # Protects secrets
│   └── requirements.txt       # Dependencies
│
└── Documentation
    ├── README.md              # Main documentation (11KB)
    ├── QUICKSTART.md          # 5-minute setup
    ├── WEB_UI_GUIDE.md        # Web architecture deep dive
    ├── TROUBLESHOOTING.md     # Common issues
    └── PROJECT_SUMMARY.md     # This file
```

---

## ✅ Production-Ready Features

- ✅ Environment variable management (`.env`)
- ✅ Secrets excluded from git (`.gitignore`)
- ✅ CORS middleware (configurable origins)
- ✅ Error handling (try/except with HTTPException)
- ✅ Health check endpoint (`/health`)
- ✅ Automatic API documentation (Swagger UI at `/docs`)
- ✅ Async throughout (non-blocking I/O)
- ✅ Type hints everywhere (Pydantic models)
- ✅ Comprehensive logging (Cognee's built-in logger)
- ✅ Modular architecture (easy to test and extend)

---

## 🎓 Perfect For

- **Students** learning AI agent development
- **Bootcamps** teaching LangChain/LangGraph
- **Workshops** on knowledge graph memory
- **Portfolios** demonstrating production-grade code
- **Tutorials** on FastAPI + React integration

---

## 📝 License

MIT — free to use, modify, and share for educational and commercial purposes.

---

## 🙏 Acknowledgments

Built as companion code for the [future-with-ai.com Academy](https://future-with-ai.com/academy/agents/cognee) lesson on building agents with persistent memory.

**Tech Stack Credits:**
- [Cognee](https://github.com/topoteretes/cognee) — Knowledge graph memory
- [LangGraph](https://github.com/langchain-ai/langgraph) — Agent orchestration
- [DeepSeek](https://platform.deepseek.com) — Affordable, capable LLM
- [FastAPI](https://fastapi.tiangolo.com) — Modern Python web framework
- [React](https://react.dev) — UI library
- [TailwindCSS](https://tailwindcss.com) — Utility-first CSS

---

**Ready to deploy to GitHub!** 🚀

All code is clean, well-documented, and follows SOLID principles. The `.gitignore` protects your API keys, and the comprehensive documentation makes it easy for students to understand and extend.
