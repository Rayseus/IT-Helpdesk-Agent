"""Optional FastAPI server for IT Helpdesk Agent."""

from __future__ import annotations

from typing import Any

from src.agent.graph import run_turn
from src.agent.state import GraphState
from src.config import get_settings

try:
    from fastapi import FastAPI
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "FastAPI is required for the API server. Install with: pip install -e '.[api]'"
    ) from exc

app = FastAPI(title="IT Helpdesk Agent API", version="0.1.0")
_sessions: dict[str, GraphState] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    employee_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    decision: str
    tools_used: list[str] = Field(default_factory=list)
    escalation_package: dict[str, Any] | None = None


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "llm_provider": settings.llm_provider}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    state = _sessions.get(request.session_id) if request.session_id else None
    result = run_turn(
        request.message,
        session_id=request.session_id,
        employee_id=request.employee_id,
        state=state,
    )
    session_id = result.get("session_id", request.session_id or "")
    _sessions[session_id] = result

    tools = list(
        dict.fromkeys(
            c.get("tool_name", "")
            for c in result.get("tool_calls", [])
            if c.get("tool_name")
        )
    )

    return ChatResponse(
        session_id=session_id,
        reply=result.get("assistant_reply") or "",
        decision=result.get("decision") or "unknown",
        tools_used=tools,
        escalation_package=result.get("escalation_package"),
    )


@app.get("/session/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    state = _sessions.get(session_id)
    if not state:
        return {"error": "session not found", "session_id": session_id}
    return dict(state)
