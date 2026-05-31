"""Integration tests for US5 — complex multi-system escalation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.agent.complex_handlers import (
    apply_complex_rules,
    detect_complex_systems,
    prefetch_complex_tools,
)
from src.agent.escalation import format_escalation_display
from src.agent.graph import run_turn
from src.models.schemas import Decision, EscalationPackage

SCENARIOS_FILE = (
    Path(__file__).resolve().parents[1] / "eval" / "scenarios" / "us5_pipeline_failure.yaml"
)


def _load_scenarios() -> list[dict]:
    text = SCENARIOS_FILE.read_text(encoding="utf-8")
    return [d for d in yaml.safe_load_all(text) if d]


def _tool_names(state: dict) -> set[str]:
    return {c.get("tool_name") for c in state.get("tool_calls", []) if c.get("tool_name")}


@pytest.mark.integration
@pytest.mark.parametrize("scenario", _load_scenarios(), ids=lambda s: s["name"])
def test_us5_eval_scenario(scenario: dict):
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
def test_us5_pipeline_failure_full_escalation_package():
    message = (
        "Our data pipeline failed after the IT maintenance window last week. "
        "Jenkins jobs are timing out and Tableau dashboards are showing stale data."
    )
    state = run_turn(message, employee_id="emp-002")

    assert state["decision"] == Decision.ESCALATE.value
    assert {"status_check", "history_search"}.issubset(_tool_names(state))

    pkg_raw = state.get("escalation_package")
    assert pkg_raw is not None
    package = EscalationPackage.model_validate(pkg_raw)
    assert package.target_team == "Data Platform"
    assert package.recommended_priority.value in {"P1", "P2", "P3"}
    assert package.attempted_steps
    assert "jenkins" in package.tool_results_summary.lower() or "Jenkins" in package.tool_results_summary

    display = format_escalation_display(package)
    assert "ESCALATION PACKAGE" in display
    assert "Timeline:" in display
    assert "Tools Checked:" in display


@pytest.mark.unit
def test_detect_complex_systems():
    msg = "Jenkins timeout and Tableau stale after pipeline failure"
    systems = detect_complex_systems(msg)
    assert "jenkins" in systems
    assert "tableau" in systems


@pytest.mark.unit
def test_complex_prefetch_tools():
    message = "Pipeline failure jenkins timeout tableau stale"
    records, systems = prefetch_complex_tools("emp-002", message)
    names = {r["tool_name"] for r in records}
    assert "status_check" in names
    assert "history_search" in names
    assert len(systems) >= 2


@pytest.mark.unit
def test_complex_rules_always_escalate():
    message = "Jenkins jobs timing out, Tableau dashboards stale after maintenance"
    records, _ = prefetch_complex_tools("emp-002", message)
    decision, reply, team, steps, timeline, priority = apply_complex_rules(records, message)
    assert decision == Decision.ESCALATE.value
    assert team == "Data Platform"
    assert len(steps) >= 2
    assert "maintenance" in timeline.lower() or "User report" in timeline
    assert priority in {"P1", "P2", "P3"}
