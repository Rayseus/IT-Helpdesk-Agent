"""Integration tests for US2 — Salesforce performance scenarios."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.agent.graph import run_turn
from src.agent.software_handlers import (
    apply_software_performance_rules,
    needs_software_clarify,
    prefetch_software_tools,
    software_clarify_questions,
)
from src.models.schemas import Decision

SCENARIOS_FILE = Path(__file__).resolve().parents[1] / "eval" / "scenarios" / "us2_salesforce_slow.yaml"


def _load_scenarios() -> list[dict]:
    text = SCENARIOS_FILE.read_text(encoding="utf-8")
    return [d for d in yaml.safe_load_all(text) if d]


def _tool_names(state: dict) -> set[str]:
    return {c.get("tool_name") for c in state.get("tool_calls", []) if c.get("tool_name")}


@pytest.mark.integration
@pytest.mark.parametrize("scenario", _load_scenarios(), ids=lambda s: s["name"])
def test_us2_eval_scenario(scenario: dict):
    message = scenario["turns"][0]
    employee = scenario.get("user_persona")
    state = run_turn(message, employee_id=employee)

    assert state.get("decision") == scenario["expected_decision"]
    tools = _tool_names(state)
    for expected in scenario.get("expected_tools", []):
        assert expected in tools, f"missing {expected}, got {tools}"

    reply = (state.get("assistant_reply") or "").lower()
    for phrase in scenario.get("must_contain", []):
        assert phrase.lower() in reply
    for phrase in scenario.get("must_not_contain", []):
        assert phrase.lower() not in reply


@pytest.mark.integration
def test_us2_chicago_regional_outage_resolve_with_eta():
    message = (
        "Salesforce has been loading extremely slowly since yesterday. "
        "My teammates in the Chicago office are seeing the same thing."
    )
    state = run_turn(message, employee_id="emp-001")

    assert state["decision"] == Decision.RESOLVE.value
    assert {"user_lookup", "status_check"}.issubset(_tool_names(state))
    reply = state["assistant_reply"].lower()
    assert "degraded" in reply or "known" in reply or "platform" in reply
    assert "escalat" not in reply


@pytest.mark.integration
def test_us2_vague_message_clarifies():
    message = "Salesforce is really slow today."
    state = run_turn(message, employee_id="emp-001")

    assert state["decision"] == Decision.CLARIFY.value
    assert len(state.get("tool_calls") or []) == 0
    assert "teammate" in state["assistant_reply"].lower() or "browser" in state["assistant_reply"].lower()


@pytest.mark.unit
def test_needs_software_clarify():
    assert needs_software_clarify("Salesforce is really slow today.") is True
    assert needs_software_clarify(
        "Salesforce slow, teammates in Chicago office same issue"
    ) is False


@pytest.mark.unit
def test_software_prefetch_tools():
    records = prefetch_software_tools("emp-001", "salesforce slow loading")
    names = {r["tool_name"] for r in records}
    assert {"user_lookup", "status_check", "kb_search", "history_search"}.issubset(names)


@pytest.mark.unit
def test_software_rules_regional_outage():
    message = "Salesforce slow, teammates in Chicago office seeing same thing"
    records = prefetch_software_tools("emp-001", message)
    decision, reply, _ = apply_software_performance_rules(records, message)
    assert decision == Decision.RESOLVE.value
    assert "degraded" in reply.lower() or "known" in reply.lower()


@pytest.mark.unit
def test_software_clarify_questions_content():
    qs = software_clarify_questions()
    assert len(qs) >= 2
    assert any("teammate" in q.lower() for q in qs)
