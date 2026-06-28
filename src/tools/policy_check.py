"""Policy check tool."""

from __future__ import annotations

from src.models.schemas import PolicyRule, ToolResponse
from src.paths import DATA_DIR
from src.tools.base import fail, load_json, ok
from src.tools.user_lookup import user_lookup

RULES_FILE = DATA_DIR / "policies" / "rules.json"


def _load_rules() -> list[PolicyRule]:
    data = load_json(RULES_FILE)
    return [PolicyRule.model_validate(r) for r in data.get("rules", [])]


def policy_check(action: str, employee_id: str, context: str | None = None) -> ToolResponse:
    if not action.strip():
        return fail("policy_check", "action is required")
    if not employee_id.strip():
        return fail("policy_check", "employee_id is required")

    user_result = user_lookup(employee_id=employee_id)
    if not user_result.success:
        return fail("policy_check", "employee_not_found")

    rules = _load_rules()
    rule = next((r for r in rules if r.action == action), None)
    if not rule:
        return fail("policy_check", f"unknown action: {action}")

    employee = user_result.data or {}
    can_execute = rule.agent_can_execute

    # Role-based override for grafana
    if action == "grant_grafana_readonly":
        dept = employee.get("department", "")
        can_execute = dept in {"Data Engineering", "Engineering", "SRE"}

    if action == "grant_snowflake_dev":
        can_execute = employee.get("department") == "Data Engineering"

    result = {
        "action": rule.action,
        "agent_can_execute": can_execute,
        "approval_required": rule.approval_required.value,
        "conditions": rule.conditions,
        "description": rule.description,
        "recommended_escalation_team": rule.recommended_escalation_team,
        "context": context,
        "employee_id": employee_id,
    }
    return ok("policy_check", result)
