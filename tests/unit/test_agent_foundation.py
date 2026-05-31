"""Unit tests for agent foundation (no LLM)."""

import pytest

from src.agent.escalation import build_escalation_package, format_escalation_display
from src.agent.nodes import _detect_category, _is_vague, route_after_intake
from src.agent.state import make_initial_state
from src.models.schemas import Decision


@pytest.mark.unit
def test_detect_category_password():
    assert _detect_category("I can't log into Okta") == "password"


@pytest.mark.unit
def test_detect_category_vpn():
    assert _detect_category("VPN keeps disconnecting") == "vpn"


@pytest.mark.unit
def test_is_vague():
    assert _is_vague("my computer is broken") is True
    assert _is_vague("Salesforce has been loading slowly since yesterday") is False


@pytest.mark.unit
def test_route_after_intake_clarify():
    state = make_initial_state("sess-1")
    state["decision"] = Decision.CLARIFY.value
    assert route_after_intake(state) == "clarify"


@pytest.mark.unit
def test_clarify_decision_does_not_stick_on_next_turn():
    """After a vague message, a specific follow-up must not keep routing to clarify."""
    from src.agent.graph import run_turn

    state = run_turn("My computer is broken. Help me.", employee_id="emp-001")
    assert state["decision"] == Decision.CLARIFY.value

    state = run_turn(
        "My VPN keeps disconnecting every 10-15 minutes.",
        state=state,
    )
    assert state["decision"] == Decision.RESOLVE.value


@pytest.mark.unit
def test_escalation_package_builder():
    package = build_escalation_package(
        issue_summary="Okta login failure",
        timeline="Started 09:00 today",
        employee={"id": "emp-001", "name": "Jane", "email": "jane.doe@company.com", "department": "Sales", "role": "AE", "location": "Chicago"},
        diagnosis={"hypothesis": "MFA lock", "confidence": 0.8, "category": "password"},
        tool_calls=[{"tool_name": "user_lookup", "success": True, "output": {"data": {"account_status": "locked"}}}],
    )
    display = format_escalation_display(package)
    assert "ESCALATION PACKAGE" in display
    assert "Okta login failure" in display
