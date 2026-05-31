"""VPN and connectivity issue handling (US3)."""

from __future__ import annotations

import re
from typing import Any

from src.models.schemas import Decision
from src.tools.kb_format import kb_article_text
from src.tools.registry import invoke_tool, to_tool_call_record

PERSIST_PATTERNS = [
    r"still (disconnect|drop|happen)",
    r"still (not working|broken|failing)",
    r"tried everything",
    r"already (updated|tried|checked|rebooted)",
    r"doesn'?t (help|work)",
    r"no luck",
    r"persist",
    r"after (all|these) steps",
]

ATTEMPTED_STEP_PATTERNS: list[tuple[str, str]] = [
    (r"updated? (globalprotect|client|vpn)", "Updated GlobalProtect client"),
    (r"reboot(ed)? (router|wifi|network)", "Rebooted home router / Wi-Fi"),
    (r"cert(ificate)?", "Checked VPN device certificate"),
    (r"clear(ed)? config", "Cleared GlobalProtect config"),
    (r"wired|ethernet", "Tested wired connection"),
]


def vpn_persist_detected(message: str) -> bool:
    lower = message.lower()
    return any(re.search(p, lower) for p in PERSIST_PATTERNS)


def extract_attempted_steps(message: str) -> list[str]:
    lower = message.lower()
    steps: list[str] = []
    for pattern, label in ATTEMPTED_STEP_PATTERNS:
        if re.search(pattern, lower):
            steps.append(label)
    return steps or ["Self-service KB steps attempted via agent conversation"]


def prefetch_vpn_tools(
    employee_id: str | None,
    query: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    if employee_id:
        resp = invoke_tool("user_lookup", employee_id=employee_id)
        records.append(
            to_tool_call_record("user_lookup", {"employee_id": employee_id}, resp).model_dump(
                mode="json"
            )
        )

    status_kwargs = {"service_id": "vpn-gateway"}
    resp = invoke_tool("status_check", **status_kwargs)
    records.append(
        to_tool_call_record("status_check", status_kwargs, resp).model_dump(mode="json")
    )

    kb_query = query if query.strip() else "VPN frequent disconnect troubleshooting"
    resp = invoke_tool("kb_search", query=kb_query, category="vpn")
    records.append(
        to_tool_call_record("kb_search", {"query": kb_query, "category": "vpn"}, resp).model_dump(
            mode="json"
        )
    )

    return records


def _tool_data(records: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for record in records:
        if record.get("tool_name") != name or not record.get("success"):
            continue
        output = record.get("output") or {}
        return output.get("data")
    return None


def _kb_runbook_block(articles: list[dict[str, Any]]) -> str:
    if not articles:
        return ""
    article = articles[0]
    body = kb_article_text(article, for_reply=True)
    if not body:
        return ""
    title = article.get("title", "VPN troubleshooting runbook")
    return f"**{title}**\n\n{body}"


def apply_vpn_rules(
    tool_records: list[dict[str, Any]],
    user_message: str,
) -> tuple[str, str, str | None, list[str]]:
    """Return decision, reply, escalation team, attempted steps."""
    user = _tool_data(tool_records, "user_lookup")
    status = _tool_data(tool_records, "status_check")
    kb = _tool_data(tool_records, "kb_search")
    articles = (kb or {}).get("articles") or []

    user_name = (user or {}).get("name", "there")
    equipment = (user or {}).get("equipment") or []
    device_note = f" (registered devices: {', '.join(equipment)})" if equipment else ""

    health = (status or {}).get("health", "unknown")
    eta = status.get("eta_resolution") if status else None
    service_name = (status or {}).get("name") or "GlobalProtect VPN Gateway"
    description = (status or {}).get("description") or ""
    kb_block = _kb_runbook_block(articles)

    attempted = extract_attempted_steps(user_message)

    if vpn_persist_detected(user_message) and health != "maintenance":
        diagnostic_lines = [
            f"Employee: {user_name}{device_note}",
            f"VPN gateway health: {health}",
            f"Issue: {user_message[:200]}",
            f"Tools checked: user_lookup, status_check, kb_search",
        ]
        if kb_block:
            diagnostic_lines.append(f"KB reference: {articles[0].get('title', 'vpn runbook')}")

        reply = (
            "I've reviewed your VPN issue and the self-service steps haven't resolved it.\n\n"
            "**Diagnostic summary:**\n"
            + "\n".join(f"- {line}" for line in diagnostic_lines)
            + "\n\nI'm escalating this to our Network / VPN team with the full context above."
        )
        return Decision.ESCALATE.value, reply, "Network / VPN Team", attempted

    if health == "maintenance":
        reply = (
            f"Hi {user_name}, I checked our VPN gateway status.\n\n"
            f"**{service_name}** is currently in a **scheduled maintenance window**.\n"
            f"Details: {description}\n"
            f"**Estimated completion:** {eta or 'check status page'}\n\n"
            "During maintenance, sessions may drop every 10–15 minutes — this can match what you're seeing.\n\n"
            "**Recommended now:**\n"
            "1. Wait for the maintenance window to complete.\n"
            "2. Use web-only apps (Okta SSO apps) that don't require full VPN if urgent.\n"
            "3. Avoid reconnect loops — they'll stabilize after maintenance.\n\n"
        )
        if kb_block:
            reply += f"**When VPN is stable again**, follow our runbook:\n\n{kb_block}"
        return Decision.RESOLVE.value, reply, None, attempted

    if health in ("degraded", "outage"):
        reply = (
            f"**{service_name}** is currently **{health}**.\n"
            f"{description}\n"
            f"**ETA:** {eta or 'TBD'}\n\n"
            "This may cause disconnects. Wait for service recovery or use web-only access where possible."
        )
        return Decision.RESOLVE.value, reply, None, attempted

    reply = (
        f"Hi {user_name}, let's walk through VPN troubleshooting step by step.\n\n"
        f"Gateway status is **{health}** — no platform-wide issue detected.\n\n"
    )
    if kb_block:
        reply += f"{kb_block}\n\n"
    reply += (
        "Reply with what you've tried if the issue persists — "
        "I'll escalate with a full diagnostic summary."
    )
    return Decision.RESOLVE.value, reply, None, attempted
