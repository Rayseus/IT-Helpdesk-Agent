"""LangGraph conversation state types."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from src.models.schemas import (
    Decision,
    Diagnosis,
    EscalationPackage,
    Message,
    ToolCallRecord,
)


def merge_messages(existing: list[dict], new: list[dict]) -> list[dict]:
    return existing + new


class GraphState(TypedDict, total=False):
    session_id: str
    employee_id: str | None
    messages: Annotated[list[dict[str, Any]], merge_messages]
    diagnosis: dict[str, Any]
    # No reducer: each turn's investigate node replaces tool_calls wholesale,
    # so prior turns' tool calls don't accumulate into the next escalation package.
    tool_calls: list[dict[str, Any]]
    pending_questions: list[str]
    decision: Literal["clarify", "resolve", "escalate"] | None
    escalation_package: dict[str, Any] | None
    turn_count: int
    last_user_message: str
    assistant_reply: str
    _escalation_team: str | None
    _escalation_priority: str | None
    _escalation_timeline: str | None
    _attempted_steps: list[str] | None


def empty_diagnosis() -> dict[str, Any]:
    return Diagnosis().model_dump(mode="json")


def make_initial_state(session_id: str, employee_id: str | None = None) -> GraphState:
    return GraphState(
        session_id=session_id,
        employee_id=employee_id,
        messages=[],
        diagnosis=empty_diagnosis(),
        tool_calls=[],
        pending_questions=[],
        decision=None,
        escalation_package=None,
        turn_count=0,
        last_user_message="",
        assistant_reply="",
    )


def append_message(state: GraphState, role: str, content: str) -> dict[str, Any]:
    msg = Message(role=role, content=content)  # type: ignore[arg-type]
    return {"messages": [msg.model_dump(mode="json")]}


def set_decision(state: GraphState, decision: Decision) -> dict[str, Any]:
    return {"decision": decision.value}
