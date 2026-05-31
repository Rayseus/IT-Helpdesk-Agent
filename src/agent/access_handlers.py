"""Access and permissions request handling (US4)."""

from __future__ import annotations

import re
from typing import Any

from src.models.schemas import Decision
from src.tools.registry import invoke_tool, to_tool_call_record

ACCESS_PATTERNS: list[tuple[str, str]] = [
    (r"grafana", "grant_grafana_readonly"),
    (r"snowflake\s+(prod(uction)?|production)", "grant_snowflake_prod"),
    (r"production\s+(database|snowflake)", "grant_snowflake_prod"),
    (r"snowflake\s+(dev|staging)", "grant_snowflake_dev"),
    (r"\bsnowflake\b", "grant_snowflake_prod"),
    (r"salesforce.*(access|permission|license)", "grant_salesforce_access"),
    (r"(admin|root)\s+access", "grant_admin_access"),
]

ELIGIBLE_DEPARTMENTS: dict[str, set[str]] = {
    "grant_grafana_readonly": {"Data Engineering", "Engineering", "SRE"},
    "grant_snowflake_prod": {"Data Engineering"},
    "grant_snowflake_dev": {"Data Engineering"},
}


def detect_access_actions(message: str) -> list[str]:
    lower = message.lower()
    if not any(w in lower for w in ["access", "permission", "grant", "need", "request", "join"]):
        if not any(w in lower for w in ["grafana", "snowflake", "salesforce", "admin"]):
            return []

    found: list[str] = []
    for pattern, action in ACCESS_PATTERNS:
        if re.search(pattern, lower):
            if action not in found:
                found.append(action)
    return found


def _is_eligible(action: str, user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    allowed = ELIGIBLE_DEPARTMENTS.get(action)
    if not allowed:
        return True
    dept = user.get("department", "")
    if dept in allowed:
        return True
    if action == "grant_snowflake_prod" and "analyst" in user.get("role", "").lower():
        return True
    return False


def _already_has(user: dict[str, Any] | None, action: str) -> bool:
    perms = (user or {}).get("permissions") or []
    if action == "grant_grafana_readonly":
        return "grafana-readonly" in perms or "grafana" in perms
    if action == "grant_snowflake_dev":
        return "snowflake-dev" in perms
    if action == "grant_snowflake_prod":
        return "snowflake-prod" in perms
    return False


def prefetch_access_tools(
    employee_id: str | None,
    query: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    actions = detect_access_actions(query)

    if employee_id:
        resp = invoke_tool("user_lookup", employee_id=employee_id)
        records.append(
            to_tool_call_record("user_lookup", {"employee_id": employee_id}, resp).model_dump(
                mode="json"
            )
        )

    if not actions and employee_id:
        actions = ["grant_grafana_readonly", "grant_snowflake_prod"]

    for action in actions:
        if not employee_id:
            break
        resp = invoke_tool(
            "policy_check",
            action=action,
            employee_id=employee_id,
            context=query[:200],
        )
        records.append(
            to_tool_call_record(
                "policy_check",
                {"action": action, "employee_id": employee_id},
                resp,
            ).model_dump(mode="json")
        )

    return records, actions


def _tool_data(records: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for record in records:
        if record.get("tool_name") != name or not record.get("success"):
            continue
        output = record.get("output") or {}
        return output.get("data")
    return None


def _policy_results(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for record in records:
        if record.get("tool_name") != "policy_check" or not record.get("success"):
            continue
        output = record.get("output") or {}
        data = output.get("data")
        if data:
            results.append(data)
    return results


def _friendly_action_name(action: str) -> str:
    names = {
        "grant_grafana_readonly": "Grafana read-only dashboards",
        "grant_snowflake_prod": "Snowflake production database",
        "grant_snowflake_dev": "Snowflake dev/staging",
        "grant_salesforce_access": "Salesforce access",
        "grant_admin_access": "Admin access",
    }
    return names.get(action, action)


def apply_access_rules(
    tool_records: list[dict[str, Any]],
    user_message: str,
    actions: list[str],
) -> tuple[str, str, str | None, list[str]]:
    """Return decision, reply, escalation team, attempted steps."""
    user = _tool_data(tool_records, "user_lookup")
    policies = _policy_results(tool_records)
    user_name = (user or {}).get("name", "there")
    manager_id = (user or {}).get("manager_id", "your manager")

    if not actions:
        return (
            Decision.CLARIFY.value,
            "I'd like to help with your access request. Which systems do you need access to "
            "(e.g., Grafana, Snowflake prod, Snowflake dev)?",
            None,
            [],
        )

    granted: list[str] = []
    pending: list[dict[str, Any]] = []
    denied: list[tuple[str, str]] = []

    for policy in policies:
        action = policy.get("action", "")
        label = _friendly_action_name(action)

        if not _is_eligible(action, user):
            denied.append(
                (
                    label,
                    f"Your department/role ({user.get('department')}, {user.get('role')}) "
                    f"is not eligible for {label}. Contact your manager for the correct access path.",
                )
            )
            continue

        if _already_has(user, action) and policy.get("agent_can_execute"):
            granted.append(f"**{label}** — you already have this access in your profile.")
            continue

        if policy.get("agent_can_execute"):
            granted.append(
                f"**{label}** — ✅ **Granted (simulated)**\n"
                f"  - Policy: {policy.get('description')}\n"
                f"  - Added to appropriate Okta group; access active within ~15 minutes."
            )
            continue

        approval = policy.get("approval_required", "none")
        if approval and approval != "none":
            pending.append(policy)
        else:
            denied.append((label, policy.get("description", "Not eligible for self-service.")))

    sections: list[str] = [f"Hi {user_name}, here's your access request summary:\n"]

    if granted:
        sections.append("### ✅ Approved / Self-Service\n" + "\n\n".join(granted))

    if pending:
        pending_lines = []
        for p in pending:
            label = _friendly_action_name(p.get("action", ""))
            team = p.get("recommended_escalation_team", "IT Helpdesk")
            pending_lines.append(
                f"**{label}** — requires **{p.get('approval_required')} approval**\n"
                f"  - {p.get('description')}\n"
                f"  - Escalation team: {team}\n"
                f"  - Please provide: business justification, data scope, manager ({manager_id})"
            )
        sections.append("### ⏳ Requires Approval\n" + "\n\n".join(pending_lines))

    if denied:
        denied_lines = [f"**{label}** — ❌ **Not approved**\n  - {reason}" for label, reason in denied]
        sections.append("### ❌ Denied\n" + "\n\n".join(denied_lines))

    reply = "\n\n".join(sections)

    escalation_team = None
    if pending:
        escalation_team = pending[0].get("recommended_escalation_team", "Data Platform")
        reply += (
            f"\n\nI've opened an escalation to **{escalation_team}** for items requiring approval. "
            "A human agent will follow up with your manager."
        )
        return Decision.ESCALATE.value, reply, escalation_team, ["Policy check completed for access request"]

    if denied and not granted:
        return Decision.RESOLVE.value, reply, None, []

    if granted:
        return Decision.RESOLVE.value, reply, None, ["Simulated self-service grant per policy"]

    return Decision.CLARIFY.value, reply, None, []
