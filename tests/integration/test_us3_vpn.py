"""Integration tests for US3 — VPN disconnect scenarios."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.agent.graph import run_turn
from src.agent.vpn_handlers import (
    apply_vpn_rules,
    prefetch_vpn_tools,
    vpn_persist_detected,
)
from src.models.schemas import Decision

SCENARIOS_FILE = (
    Path(__file__).resolve().parents[1] / "eval" / "scenarios" / "us3_vpn_disconnect.yaml"
)


def _load_scenarios() -> list[dict]:
    text = SCENARIOS_FILE.read_text(encoding="utf-8")
    return [d for d in yaml.safe_load_all(text) if d]


def _tool_names(state: dict) -> set[str]:
    return {c.get("tool_name") for c in state.get("tool_calls", []) if c.get("tool_name")}


@pytest.mark.integration
@pytest.mark.parametrize("scenario", _load_scenarios(), ids=lambda s: s["name"])
def test_us3_eval_scenario(scenario: dict):
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
def test_us3_vpn_disconnect_maintenance_resolve():
    message = (
        "My VPN keeps disconnecting every 15 minutes while working remotely. "
        "I can't stay connected to internal tools."
    )
    state = run_turn(message, employee_id="emp-001")

    assert state["decision"] == Decision.RESOLVE.value
    assert {"user_lookup", "status_check", "kb_search"}.issubset(_tool_names(state))
    reply = state["assistant_reply"].lower()
    assert "maintenance" in reply
    assert "escalat" not in reply or "escalation package" not in reply


@pytest.mark.integration
def test_us3_vpn_escalate_with_diagnostic_summary():
    message = (
        "VPN still disconnects every 15 minutes. I already updated GlobalProtect, "
        "rebooted my router, and checked the certificate — still not working."
    )
    records = prefetch_vpn_tools("emp-001", message)
    # Simulate healthy gateway for escalation path (maintenance would defer to wait)
    for record in records:
        if record.get("tool_name") == "status_check":
            output = record.setdefault("output", {})
            data = output.setdefault("data", {})
            data["health"] = "healthy"
            data["description"] = "All regions operating normally"
            data["eta_resolution"] = None

    decision, reply, team, attempted = apply_vpn_rules(records, message)
    assert decision == Decision.ESCALATE.value
    assert team == "Network / VPN Team"
    assert "diagnostic" in reply.lower()
    assert len(attempted) >= 1


@pytest.mark.unit
def test_vpn_prefetch_tools():
    records = prefetch_vpn_tools("emp-001", "VPN disconnect every 15 minutes")
    names = {r["tool_name"] for r in records}
    assert {"user_lookup", "status_check", "kb_search"}.issubset(names)


@pytest.mark.unit
def test_vpn_persist_detected():
    assert vpn_persist_detected("I already updated GlobalProtect but still disconnecting") is True
    assert vpn_persist_detected("VPN disconnects every 15 minutes") is False


@pytest.mark.unit
def test_vpn_rules_maintenance_window():
    message = "VPN disconnects every 15 minutes on GlobalProtect"
    records = prefetch_vpn_tools("emp-001", message)
    decision, reply, team, _ = apply_vpn_rules(records, message)
    assert decision == Decision.RESOLVE.value
    assert team is None
    assert "maintenance" in reply.lower()
