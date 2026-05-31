"""Complex multi-system issue handling (US5)."""

from __future__ import annotations

from typing import Any

from src.models.schemas import Decision, Priority
from src.tools.registry import invoke_tool, to_tool_call_record

COMPLEX_SYSTEM_KEYWORDS = ["jenkins", "tableau", "pipeline"]


def detect_complex_systems(message: str) -> list[str]:
    lower = message.lower()
    systems: list[str] = []
    if "jenkins" in lower or "pipeline" in lower:
        systems.append("jenkins")
    if "tableau" in lower:
        systems.append("tableau")
    return systems or ["jenkins", "tableau"]


def prefetch_complex_tools(
    employee_id: str | None,
    query: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    systems = detect_complex_systems(query)

    if employee_id:
        resp = invoke_tool("user_lookup", employee_id=employee_id)
        records.append(
            to_tool_call_record("user_lookup", {"employee_id": employee_id}, resp).model_dump(
                mode="json"
            )
        )

    for service_id in systems:
        resp = invoke_tool("status_check", service_id=service_id)
        records.append(
            to_tool_call_record(
                "status_check", {"service_id": service_id}, resp
            ).model_dump(mode="json")
        )

    resp = invoke_tool("history_search", query=query, systems=systems)
    records.append(
        to_tool_call_record(
            "history_search", {"query": query, "systems": systems}, resp
        ).model_dump(mode="json")
    )

    return records, systems


def _tool_data_list(records: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for record in records:
        if record.get("tool_name") != name or not record.get("success"):
            continue
        output = record.get("output") or {}
        data = output.get("data")
        if data:
            results.append(data)
    return results


def _history_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    data = _tool_data_list(records, "history_search")
    if not data:
        return []
    return data[0].get("records") or []


def build_complex_timeline(
    user_message: str,
    status_results: list[dict[str, Any]],
    history_records: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lower = user_message.lower()

    if "maintenance" in lower:
        lines.append("- IT maintenance window cited as likely trigger")

    for status in status_results:
        service = status.get("name") or status.get("service_id", "service")
        for change in status.get("recent_changes") or []:
            ts = change.get("timestamp", "")
            desc = change.get("description", "")
            impact = change.get("impact", "")
            lines.append(f"- [{ts}] {service}: {desc} — {impact}")

    if history_records:
        hist = history_records[0]
        lines.append(
            f"- Prior incident ({hist.get('id', 'history')}): "
            f"{hist.get('problem_summary')} → {hist.get('resolution', 'resolved')}"
        )

    lines.append(f"- User report: {user_message[:160]}")
    return "\n".join(lines)


def infer_complex_priority(user_message: str, status_results: list[dict[str, Any]]) -> str:
    lower = user_message.lower()
    if any(w in lower for w in ["urgent", "executive", "production down", "blocking"]):
        return Priority.P1.value
    if any(s.get("health") in ("outage", "degraded") for s in status_results):
        return Priority.P2.value
    return Priority.P3.value


def apply_complex_rules(
    tool_records: list[dict[str, Any]],
    user_message: str,
) -> tuple[str, str, str, list[str], str, str]:
    """Return decision, reply, team, attempted_steps, timeline, priority."""
    status_results = _tool_data_list(tool_records, "status_check")
    history_records = _history_records(tool_records)
    systems = detect_complex_systems(user_message)

    status_lines: list[str] = []
    for status in status_results:
        name = status.get("name") or status.get("service_id", "Unknown")
        health = status.get("health", "unknown")
        desc = status.get("description", "")
        eta = status.get("eta_resolution")
        eta_note = f" ETA: {eta}" if eta else ""
        status_lines.append(f"- **{name}**: {health} — {desc}{eta_note}")

    hist_note = ""
    if history_records:
        hist = history_records[0]
        hist_note = (
            f"\n\n**Similar past incident** ({hist.get('id', 'history')}): "
            f"{hist.get('problem_summary')}. "
            f"Resolution: {hist.get('resolution', 'See history')}"
        )

    reply = (
        "This is a **multi-system data platform issue** beyond automated troubleshooting scope.\n\n"
        "**Systems checked:**\n"
        + "\n".join(status_lines)
        + hist_note
        + "\n\n"
        "I've gathered status and history for Data Platform. "
        "This requires platform team investigation — escalating now with full context."
    )

    attempted = [
        "Queried Jenkins and Tableau service status",
        "Searched resolution history for pipeline failures",
        "Confirmed issue spans multiple systems — not user-fixable",
    ]

    timeline = build_complex_timeline(user_message, status_results, history_records)
    priority = infer_complex_priority(user_message, status_results)

    return (
        Decision.ESCALATE.value,
        reply,
        "Data Platform",
        attempted,
        timeline,
        priority,
    )
