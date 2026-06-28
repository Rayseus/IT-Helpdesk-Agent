"""LangGraph state machine for IT Helpdesk Agent."""

from __future__ import annotations

import uuid
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from src.agent.nodes import (
    clarify_node,
    decide_node,
    escalate_node,
    intake_node,
    investigate_node,
    investigate_password_node,
    investigate_software_node,
    investigate_vpn_node,
    investigate_access_node,
    investigate_complex_node,
    respond_node,
    route_after_intake,
    route_after_investigate,
)
from src.agent.state import GraphState, make_initial_state
from src.logging_config import configure_logging, get_logger

logger = get_logger(__name__)


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("intake", intake_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("investigate", investigate_node)
    graph.add_node("investigate_password", investigate_password_node)
    graph.add_node("investigate_software", investigate_software_node)
    graph.add_node("investigate_vpn", investigate_vpn_node)
    graph.add_node("investigate_access", investigate_access_node)
    graph.add_node("investigate_complex", investigate_complex_node)
    graph.add_node("decide", decide_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("respond", respond_node)

    graph.add_edge(START, "intake")
    graph.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "clarify": "clarify",
            "respond": "respond",
            "investigate": "investigate",
            "investigate_password": "investigate_password",
            "investigate_software": "investigate_software",
            "investigate_vpn": "investigate_vpn",
            "investigate_access": "investigate_access",
            "investigate_complex": "investigate_complex",
        },
    )
    graph.add_edge("clarify", END)
    graph.add_edge("investigate", "decide")
    graph.add_edge("investigate_password", "decide")
    graph.add_edge("investigate_software", "decide")
    graph.add_edge("investigate_vpn", "decide")
    graph.add_edge("investigate_access", "decide")
    graph.add_edge("investigate_complex", "decide")
    graph.add_conditional_edges(
        "decide",
        route_after_investigate,
        {"escalate": "escalate", "clarify": "clarify", "respond": "respond"},
    )
    graph.add_edge("escalate", END)
    graph.add_edge("respond", END)

    return graph.compile()


@lru_cache(maxsize=1)
def get_compiled_graph():
    """Compiled graph is stateless (state is passed per invoke), so reuse it."""
    return build_graph()


def run_turn(
    user_message: str,
    *,
    session_id: str | None = None,
    employee_id: str | None = None,
    state: GraphState | None = None,
) -> GraphState:
    configure_logging()
    app = get_compiled_graph()

    if state is None:
        state = make_initial_state(session_id or str(uuid.uuid4()), employee_id)
    else:
        if employee_id and not state.get("employee_id"):
            state = {**state, "employee_id": employee_id}

    state = {**state, "last_user_message": user_message}
    result = app.invoke(state)
    logger.info(
        "agent_turn_complete",
        session_id=result.get("session_id"),
        decision=result.get("decision"),
        tools=len(result.get("tool_calls", [])),
    )
    return result
