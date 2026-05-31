"""Software and application performance issue handling (US2)."""

from __future__ import annotations

import re
from typing import Any

from src.models.schemas import Decision
from src.tools.kb_format import kb_article_text
from src.tools.registry import invoke_tool, to_tool_call_record

TEAM_SCOPE_PATTERNS = [
    r"teammates?",
    r"colleagues?",
    r"coworkers?",
    r"office",
    r"same thing",
    r"everyone",
    r"whole team",
    r"others (too|also)",
]

PERSONAL_SCOPE_PATTERNS = [
    r"only me",
    r"just me",
    r"only my",
    r"just my",
    r"only i",
    r"teammates? (are )?fine",
    r"colleagues? (are )?fine",
    r"others (are )?fine",
]


def detect_service_id(message: str) -> str:
    lower = message.lower()
    if "salesforce" in lower:
        return "salesforce"
    if "tableau" in lower:
        return "tableau"
    if "jenkins" in lower:
        return "jenkins"
    return "salesforce"


def needs_software_clarify(message: str) -> bool:
    """True when performance issue lacks scope (team vs personal)."""
    lower = message.lower()
    if not any(w in lower for w in ["slow", "loading", "timeout", "performance", "lag"]):
        return False
    if any(re.search(p, lower) for p in TEAM_SCOPE_PATTERNS):
        return False
    if any(re.search(p, lower) for p in PERSONAL_SCOPE_PATTERNS):
        return False
    return True


def software_clarify_questions() -> list[str]:
    return [
        "Is this affecting only you, or are teammates in your office seeing the same issue?",
        "Which browser are you using, and do you see a specific error message or just slowness?",
    ]


def team_scope_detected(message: str) -> bool:
    lower = message.lower()
    if any(
        phrase in lower
        for phrase in [
            "teammates are fine",
            "teammates fine",
            "colleagues are fine",
            "only me",
            "only my laptop",
        ]
    ):
        return False
    return any(re.search(p, lower) for p in TEAM_SCOPE_PATTERNS)


def prefetch_software_tools(
    employee_id: str | None,
    query: str,
    service_id: str | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    service = service_id or detect_service_id(query)
    region: str | None = None

    if employee_id:
        resp = invoke_tool("user_lookup", employee_id=employee_id)
        records.append(
            to_tool_call_record("user_lookup", {"employee_id": employee_id}, resp).model_dump(
                mode="json"
            )
        )
        if resp.success and resp.data:
            region = resp.data.get("location")

    status_kwargs: dict[str, Any] = {"service_id": service}
    if region:
        status_kwargs["region"] = region
    resp = invoke_tool("status_check", **status_kwargs)
    records.append(to_tool_call_record("status_check", status_kwargs, resp).model_dump(mode="json"))

    kb_query = query if query.strip() else f"{service} slow performance"
    resp = invoke_tool("kb_search", query=kb_query, category="software")
    records.append(
        to_tool_call_record("kb_search", {"query": kb_query, "category": "software"}, resp).model_dump(
            mode="json"
        )
    )

    resp = invoke_tool("history_search", query=kb_query, systems=[service])
    records.append(
        to_tool_call_record(
            "history_search", {"query": kb_query, "systems": [service]}, resp
        ).model_dump(mode="json")
    )

    return records


def _tool_data(records: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for record in records:
        if record.get("tool_name") != name or not record.get("success"):
            continue
        output = record.get("output") or {}
        return output.get("data")
    return None


def _region_matches(user_location: str | None, affected_regions: list[str]) -> bool:
    if not user_location or not affected_regions:
        return False
    loc = user_location.lower()
    return any(loc in r.lower() or r.lower() in loc for r in affected_regions)


def apply_software_performance_rules(
    tool_records: list[dict[str, Any]],
    user_message: str,
) -> tuple[str, str, str | None]:
    user = _tool_data(tool_records, "user_lookup")
    status = _tool_data(tool_records, "status_check")
    kb = _tool_data(tool_records, "kb_search")
    history = _tool_data(tool_records, "history_search")
    articles = (kb or {}).get("articles") or []
    hist_records = (history or {}).get("records") or []

    user_location = (user or {}).get("location")
    team_issue = team_scope_detected(user_message)
    personal_only = any(re.search(p, user_message.lower()) for p in PERSONAL_SCOPE_PATTERNS)

    health = (status or {}).get("health")
    affected = (status or {}).get("affected_regions") or []
    region_hit = _region_matches(user_location, affected)

    if not personal_only and health in ("degraded", "outage") and (team_issue or region_hit):
        eta = status.get("eta_resolution") or "soon"
        service_name = status.get("name") or status.get("service_id", "the service")
        regions = ", ".join(affected) if affected else "your region"
        hist_note = ""
        if hist_records:
            hist_note = (
                f"\n\nSimilar issue resolved before: {hist_records[0].get('resolution', '')}"
            )
        reply = (
            f"This looks like a **known platform issue**, not something wrong with your device.\n\n"
            f"**{service_name}** is currently **{health}** affecting {regions}.\n"
            f"Details: {status.get('description', 'Elevated latency reported')}\n"
            f"**Estimated resolution:** {eta}\n\n"
            "No ticket needed — your team is already aware. "
            "You can wait for the fix or try again after the ETA."
            f"{hist_note}"
        )
        return Decision.RESOLVE.value, reply, None

    if health in ("degraded", "outage") and not personal_only:
        eta = status.get("eta_resolution") or "soon"
        reply = (
            f"There is a known issue with **{status.get('name', 'the service')}** "
            f"(status: {health}). ETA: {eta}.\n\n"
            "If your teammates are also affected, this is likely regional — no individual fix needed."
        )
        return Decision.RESOLVE.value, reply, None

    if personal_only or health == "healthy":
        body = kb_article_text(articles[0], for_reply=True) if articles else ""
        title = articles[0].get("title", "Performance troubleshooting") if articles else "KB guide"
        reply = (
            f"Since this appears to affect **only you**, let's try personal troubleshooting "
            f"from **{title}**:\n\n"
            f"{body}\n\n"
            "**Quick steps:**\n"
            "1. Hard refresh (Cmd+Shift+R) or try Chrome incognito.\n"
            "2. Disable browser extensions / ad blockers.\n"
            "3. Clear site cookies for the application.\n"
            "4. Compare performance on VPN vs off VPN.\n\n"
            "Tell me if none of these help — I'll escalate to IT."
        )
        return Decision.RESOLVE.value, reply, None

    if articles:
        reply = (
            f"I found **{articles[0].get('title')}** in our knowledge base. "
            "First, check if teammates have the same issue (regional outage) "
            "or if it's just your machine.\n\n"
            f"{kb_article_text(articles[0], for_reply=True)}"
        )
        return Decision.CLARIFY.value, reply, None

    return Decision.CLARIFY.value, (
        "I need a bit more detail: is this affecting only you or your whole office? "
        "Which browser are you using?"
    ), None
