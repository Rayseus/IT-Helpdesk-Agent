"""Integration tests for US4 — access and permissions scenarios."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.agent.access_handlers import (
    apply_access_rules,
    detect_access_actions,
    prefetch_access_tools,
)
from src.agent.graph import run_turn
from src.models.schemas import Decision

SCENARIOS_FILE = (
    Path(__file__).resolve().parents[1] / "eval" / "scenarios" / "us4_access_request.yaml"
)


def _load_scenarios() -> list[dict]:
    text = SCENARIOS_FILE.read_text(encoding="utf-8")
    return [d for d in yaml.safe_load_all(text) if d]


def _tool_names(state: dict) -> set[str]:
    return {c.get("tool_name") for c in state.get("tool_calls", []) if c.get("tool_name")}


@pytest.mark.integration
@pytest.mark.parametrize("scenario", _load_scenarios(), ids=lambda s: s["name"])
def test_us4_eval_scenario(scenario: dict):
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
def test_us4_mixed_grafana_grant_snowflake_escalate():
    message = (
        "I just joined the Data Engineering team and need access to the Snowflake production "
        "database and the internal Grafana dashboards."
    )
    state = run_turn(message, employee_id="emp-002")

    assert state["decision"] == Decision.ESCALATE.value
    assert {"user_lookup", "policy_check"}.issubset(_tool_names(state))
    reply = state["assistant_reply"].lower()
    assert "grafana" in reply
    assert "snowflake" in reply
    assert "approval" in reply or "escalat" in reply
    assert state.get("escalation_package") is not None


@pytest.mark.integration
def test_us4_sales_snowflake_denied():
    message = "I need access to the Snowflake production database for a sales report."
    state = run_turn(message, employee_id="emp-001")

    assert state["decision"] == Decision.RESOLVE.value
    reply = state["assistant_reply"].lower()
    assert "not eligible" in reply or "denied" in reply


@pytest.mark.unit
def test_detect_access_actions_mixed():
    msg = "Need Snowflake production database and Grafana dashboards access"
    actions = detect_access_actions(msg)
    assert "grant_grafana_readonly" in actions
    assert "grant_snowflake_prod" in actions


@pytest.mark.unit
def test_access_prefetch_tools():
    message = "Need Grafana and Snowflake prod access"
    records, actions = prefetch_access_tools("emp-002", message)
    names = {r["tool_name"] for r in records}
    assert "user_lookup" in names
    assert "policy_check" in names
    assert len(actions) >= 2


@pytest.mark.unit
def test_access_rules_grafana_self_service():
    message = "I need Grafana dashboard access"
    records, actions = prefetch_access_tools("emp-002", message)
    decision, reply, team, _ = apply_access_rules(records, message, actions)
    assert decision == Decision.RESOLVE.value
    assert team is None
    assert "grafana" in reply.lower()
