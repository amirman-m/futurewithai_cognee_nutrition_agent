"""
app.py — FastAPI Web Server for NutriAgent
===========================================
Single responsibility: HTTP server that exposes the agent via REST API
and serves the static web UI.

Architecture:
  - POST /api/chat → synchronous chat endpoint (simple, works everywhere)
  - WebSocket /ws/chat → streaming chat (optional, for real-time UX)
  - GET / → serves the React chat UI
  - Static files served from ./static/

Why FastAPI?
  - Native async support (works with our async agent)
  - Automatic OpenAPI docs at /docs
  - WebSocket support built-in
  - Minimal boilerplate for educational code
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import build_agent
from memory import get_user_profile, list_user_profiles, store_user_profile

# ── Environment ───────────────────────────────────────────────────────────────

load_dotenv()

# ── Request/Response Models ───────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Request body for POST /api/chat endpoint."""

    user_id: str
    message: str


class ChatResponse(BaseModel):
    """Response body for POST /api/chat endpoint."""

    user_id: str
    message: str
    response: str


class ProfileRequest(BaseModel):
    """Request body for POST /api/profile endpoint."""

    user_id: str
    name: str
    calorie_goal: int
    restrictions: list[str]
    allergies: list[str]
    goals: str


class ProfileSummaryResponse(BaseModel):
    """Summary response for listing saved profiles."""

    user_id: str
    name: str
    calorie_goal: int
    restrictions: list[str]
    allergies: list[str]
    goals: str
    updated_at: str | None = None


# ── Application Lifecycle ─────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager — runs on startup and shutdown.

    On startup:
      - Compile the LangGraph agent once (shared across all requests).
      - Optionally pre-load a demo user profile for testing.

    On shutdown:
      - Clean up resources if needed (none currently).
    """
    # Startup: build the agent
    app.state.agent = build_agent()

    # Optional: create a demo user for testing
    # Uncomment if you want a pre-loaded user on every server start
    # await store_user_profile(
    #     "demo_user",
    #     {
    #         "name": "Demo User",
    #         "calorie_goal": 2000,
    #         "restrictions": ["vegetarian"],
    #         "allergies": [],
    #         "goals": "maintain weight, eat healthier",
    #     },
    # )

    yield  # Server is running

    # Shutdown: cleanup (none needed currently)


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="NutriAgent API",
    description="Personalized AI nutrition assistant with persistent memory",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — allows the frontend to call the API from any origin
# In production, restrict this to your actual frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to ["http://localhost:3000"] for stricter security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API Endpoints ─────────────────────────────────────────────────────────────


@app.get("/")
async def serve_ui():
    """
    Serve the main chat UI HTML page.

    The UI is a single-page app (SPA) built with React + TailwindCSS.
    All assets are in ./static/
    """
    return FileResponse("static/index.html")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Synchronous chat endpoint.

    Flow:
      1. Receive user message + user_id
      2. Invoke the LangGraph agent (recall → respond → remember)
      3. Return the agent's response

    This is the simplest endpoint — no streaming, just request/response.
    Perfect for students learning how the agent works.
    """
    try:
        # Invoke the agent with the full state dict
        result = await app.state.agent.ainvoke(
            {
                "user_id": request.user_id,
                "user_message": request.message,
                "memory_context": "",
                "response": "",
                "pending_memory_action": "none",
            }
        )

        return ChatResponse(
            user_id=request.user_id,
            message=request.message,
            response=result["response"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/api/profile")
async def create_profile(request: ProfileRequest) -> JSONResponse:
    """
    Create or update a user's nutrition profile.

    This is the onboarding endpoint — call this once per user before
    their first chat to set up their profile in Cognee.

    Note: cognify() takes 5–15 seconds on first call. The frontend
    should show a loading spinner during this request.
    """
    try:
        await store_user_profile(
            request.user_id,
            {
                "name": request.name,
                "calorie_goal": request.calorie_goal,
                "restrictions": request.restrictions,
                "allergies": request.allergies,
                "goals": request.goals,
            },
        )

        return JSONResponse(
            {
                "status": "success",
                "message": f"Profile created for {request.name}",
                "user_id": request.user_id,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile creation error: {str(e)}")


@app.get("/api/profiles", response_model=list[ProfileSummaryResponse])
async def get_profiles() -> list[ProfileSummaryResponse]:
    return [ProfileSummaryResponse(**profile) for profile in list_user_profiles()]


@app.get("/api/profile/{user_id}", response_model=ProfileSummaryResponse)
async def get_profile(user_id: str) -> ProfileSummaryResponse:
    profile = get_user_profile(user_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return ProfileSummaryResponse(
        user_id=profile.get("user_id", user_id),
        name=profile.get("name", "Unknown"),
        calorie_goal=profile.get("calorie_goal", 2000),
        restrictions=profile.get("restrictions", []),
        allergies=profile.get("allergies", []),
        goals=profile.get("goals", "general wellness"),
        updated_at=profile.get("updated_at"),
    )


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat (optional advanced feature).

    This allows the frontend to receive the agent's response token-by-token
    as it's generated, creating a more interactive UX.

    Protocol:
      Client sends: {"user_id": "...", "message": "..."}
      Server sends: {"type": "token", "content": "..."} (multiple times)
      Server sends: {"type": "done"} (when complete)

    Note: This requires streaming support from the LLM client.
    For educational purposes, the simple POST endpoint is recommended first.
    """
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            user_id = data.get("user_id")
            message = data.get("message")

            if not user_id or not message:
                await websocket.send_json(
                    {"type": "error", "content": "Missing user_id or message"}
                )
                continue

            # Invoke agent (non-streaming for now — streaming requires LLM changes)
            result = await app.state.agent.ainvoke(
                {
                    "user_id": user_id,
                    "user_message": message,
                    "memory_context": "",
                    "response": "",
                    "pending_memory_action": "none",
                }
            )

            # Send response back to client
            await websocket.send_json({"type": "message", "content": result["response"]})

    except WebSocketDisconnect:
        pass  # Client disconnected, cleanup happens automatically


@app.get("/health")
async def health_check():
    """Simple health check endpoint for monitoring."""
    return {"status": "healthy", "service": "nutriagent"}


# ── Static Files ──────────────────────────────────────────────────────────────

# Mount the static directory AFTER defining all API routes
# This ensures /api/* routes take precedence over static file serving
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    # static/ directory doesn't exist yet — will be created when we add the UI
    pass


# ── Development Server ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    # Run with: python app.py
    # Or: uvicorn app:app --reload
    uvicorn.run(
        "app:app",
        host="0.0.0.0",  # Accept connections from any IP (needed for Docker/remote access)
        port=8000,
        reload=True,  # Auto-reload on code changes (dev only)
    )
