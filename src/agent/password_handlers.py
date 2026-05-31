"""Password and account issue handling (US1)."""

from __future__ import annotations

from typing import Any

from src.models.schemas import Decision, Priority
from src.tools.kb_format import kb_article_text
from src.tools.registry import invoke_tool, to_tool_call_record


def prefetch_password_tools(employee_id: str | None, query: str) -> list[dict[str, Any]]:
    """Mandatory tool calls for password/account category."""
    records: list[dict[str, Any]] = []

    if employee_id:
        resp = invoke_tool("user_lookup", employee_id=employee_id)
        records.append(
            to_tool_call_record("user_lookup", {"employee_id": employee_id}, resp).model_dump(
                mode="json"
            )
        )

    kb_query = query if query.strip() else "okta password reset"
    resp = invoke_tool("kb_search", query=kb_query, category="password")
    records.append(
        to_tool_call_record("kb_search", {"query": kb_query, "category": "password"}, resp).model_dump(
            mode="json"
        )
    )

    resp = invoke_tool("status_check", service_id="okta")
    records.append(
        to_tool_call_record("status_check", {"service_id": "okta"}, resp).model_dump(mode="json")
    )

    return records


def _tool_data(records: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for record in records:
        if record.get("tool_name") != name or not record.get("success"):
            continue
        output = record.get("output") or {}
        return output.get("data")
    return None


def apply_password_account_rules(
    tool_records: list[dict[str, Any]],
    user_message: str,
) -> tuple[str, str, str | None]:
    """
    Returns (decision, reply, target_team).
    Deterministic rules for account-lock and Okta outage.
    """
    user = _tool_data(tool_records, "user_lookup")
    status = _tool_data(tool_records, "status_check")
    kb = _tool_data(tool_records, "kb_search")
    articles = (kb or {}).get("articles") or []

    urgent = any(w in user_message.lower() for w in ["urgent", "30 minute", "meeting", "asap"])

    if status and status.get("health") in ("outage", "degraded"):
        eta = status.get("eta_resolution") or "soon"
        regions = ", ".join(status.get("affected_regions") or []) or "multiple regions"
        reply = (
            f"There is a known Okta issue affecting {regions}.\n\n"
            f"Status: {status.get('description', 'Service disruption')}\n"
            f"Estimated resolution: {eta}\n\n"
            "Temporary workaround: use VPN to access internal tools that don't require Okta, "
            "or wait for the outage to clear. No ticket needed unless this persists after recovery."
        )
        return Decision.RESOLVE.value, reply, None

    if user and user.get("account_status") == "locked":
        lock_reason = user.get("lock_reason") or "unknown reason"
        reply = (
            f"Your account ({user.get('email')}) is **locked**: {lock_reason}.\n\n"
            "Self-service password reset won't work until IT unlocks your MFA binding.\n\n"
            "I'm escalating this to IT Helpdesk"
            + (" with **P1 urgency** due to your time constraint." if urgent else ".")
        )
        return Decision.ESCALATE.value, reply, "IT Helpdesk"

    kb_steps = kb_article_text(articles[0], for_reply=True) if articles else ""

    reset_already_tried = any(
        w in user_message.lower() for w in ["reset", "tried", "still doesn't", "still does not"]
    )

    if reset_already_tried and articles:
        reply = (
            "Since you've already tried password reset, let's verify a few things:\n\n"
            f"From our runbook ({articles[0].get('title', 'Okta guide')}):\n"
            f"{kb_steps}\n\n"
            "1. Clear browser cache or use incognito mode.\n"
            "2. Confirm MFA device is working — check Okta Verify app.\n"
            "3. Wait 15 minutes if you hit too many attempts.\n\n"
            "If still blocked after these steps, I'll escalate to IT Helpdesk."
        )
        return Decision.RESOLVE.value, reply, None

    if articles:
        reply = (
            f"I found a relevant guide: **{articles[0].get('title')}**\n\n"
            f"{kb_steps}\n\n"
            "Follow the self-service steps above. Tell me if you're still locked out afterward."
        )
        return Decision.RESOLVE.value, reply, None

    reply = (
        "I couldn't find a specific KB article, but I recommend the Okta self-service portal "
        "for password reset. If that fails, I'll connect you with IT Helpdesk."
    )
    return Decision.CLARIFY.value, reply, None


def escalation_priority_for_message(user_message: str) -> Priority:
    if any(w in user_message.lower() for w in ["urgent", "30 minute", "meeting", "asap"]):
        return Priority.P1
    return Priority.P2
