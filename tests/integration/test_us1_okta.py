"""Integration tests for US1 — Okta password/account scenarios."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.agent.graph import run_turn
from src.agent.password_handlers import apply_password_account_rules, prefetch_password_tools
from src.models.schemas import Decision

SCENARIOS_FILE = Path(__file__).resolve().parents[1] / "eval" / "scenarios" / "us1_okta_login.yaml"


def _load_scenarios() -> list[dict]:
    text = SCENARIOS_FILE.read_text(encoding="utf-8")
    docs = [d for d in yaml.safe_load_all(text) if d]
    return docs


def _tool_names(state: dict) -> set[str]:
    return {c.get("tool_name") for c in state.get("tool_calls", []) if c.get("tool_name")}


@pytest.mark.integration
@pytest.mark.parametrize("scenario", _load_scenarios(), ids=lambda s: s["name"])
def test_us1_eval_scenario(scenario: dict):
    message = scenario["turns"][0]
    employee = scenario.get("user_persona")

    state = run_turn(message, employee_id=employee)

    assert state.get("decision") == scenario["expected_decision"]
    tools = _tool_names(state)
    for expected in scenario["expected_tools"]:
        assert expected in tools, f"missing tool {expected}, got {tools}"

    reply = (state.get("assistant_reply") or "").lower()
    for phrase in scenario.get("must_contain", []):
        assert phrase.lower() in reply, f"expected '{phrase}' in reply"
    for phrase in scenario.get("must_not_contain", []):
        assert phrase.lower() not in reply


@pytest.mark.integration
def test_us1_active_user_password_reset_resolve():
    message = (
        "I can't log into Okta. I've tried resetting my password but it still doesn't work. "
        "I need access urgently for a client meeting in 30 minutes."
    )
    state = run_turn(message, employee_id="emp-001")

    assert state["decision"] in {Decision.RESOLVE.value, Decision.ESCALATE.value}
    assert {"user_lookup", "kb_search", "status_check"}.issubset(_tool_names(state))
    assert state.get("assistant_reply")


@pytest.mark.integration
def test_us1_locked_account_escalates():
    message = "I can't log into Okta after password reset. Urgent meeting in 30 minutes."
    state = run_turn(message, employee_id="emp-locked")

    assert state["decision"] == Decision.ESCALATE.value
    assert "locked" in state["assistant_reply"].lower()
    assert state.get("escalation_package") is not None


@pytest.mark.unit
def test_password_prefetch_required_tools():
    records = prefetch_password_tools("emp-001", "okta login failure")
    names = {r["tool_name"] for r in records}
    assert names == {"user_lookup", "kb_search", "status_check"}


@pytest.mark.unit
def test_password_rules_locked_escalate():
    records = prefetch_password_tools("emp-locked", "okta password reset failed")
    decision, reply, team = apply_password_account_rules(records, "urgent meeting in 30 minutes")
    assert decision == Decision.ESCALATE.value
    assert team == "IT Helpdesk"
    assert "locked" in reply.lower()
