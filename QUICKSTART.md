# 🚀 Quick Start Guide

Get NutriAgent running in 5 minutes.

## Prerequisites

- Python 3.10 or higher
- DeepSeek API key ([get one here](https://platform.deepseek.com/api_keys))

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/nutrition-agent.git
cd nutrition-agent

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure API key
cp .env.example .env
# Edit .env and add your DeepSeek API key
```

## Run the Web UI (Recommended)

```bash
# Windows
run_web.bat

# macOS/Linux
python app.py
```

Open your browser to **http://localhost:8000**

## Run the CLI Version

```bash
python main.py
```

## What You'll See

### Web UI
1. **Onboarding form** — enter your name, goals, dietary restrictions
2. **Chat interface** — beautiful, persistent conversation
3. **Memory across sessions** — close the browser, come back later, it remembers everything

### CLI
1. **Profile setup** — hardcoded demo user (Sarah)
2. **Terminal chat** — type messages, get responses
3. **Type `quit` to exit**

## Troubleshooting

### "TimeoutError: LLM connection test timed out"

Add to your `.env`:
```env
COGNEE_SKIP_CONNECTION_TEST=true
```

### "ModuleNotFoundError: No module named 'langgraph'"

Activate the virtual environment first:
```bash
venv\Scripts\activate
```

### First run takes 5-15 seconds

This is normal! Cognee is building the knowledge graph. Subsequent runs are fast.

## Next Steps

- Read [README.md](README.md) for full documentation
- Read [WEB_UI_GUIDE.md](WEB_UI_GUIDE.md) to understand the web interface
- Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if you encounter issues

## Project Structure

```
nutrition-agent/
├── app.py              # FastAPI web server
├── agent.py            # LangGraph agent (3-node workflow)
├── memory.py           # Cognee memory manager
├── main.py             # CLI entry point
├── static/index.html   # React chat UI
└── requirements.txt    # Dependencies
```

## Key Concepts for Students

1. **Persistent Memory** — Cognee stores user data as a knowledge graph that survives between sessions
2. **LangGraph Workflow** — recall → respond → remember (read → reason → write)
3. **Async Throughout** — all functions are `async def`, entire stack is non-blocking
4. **Modular Design** — each file has one responsibility (SOLID principles)

## Educational Value

This project demonstrates:
- ✅ Knowledge graph-based memory (Cognee)
- ✅ Agent orchestration (LangGraph)
- ✅ REST API design (FastAPI)
- ✅ Modern web UI (React + TailwindCSS)
- ✅ Clean code architecture (SOLID, DRY)
- ✅ Production-ready patterns (env vars, error handling, CORS)

Perfect for learning how to build production-grade AI agents!
