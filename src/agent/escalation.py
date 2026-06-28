"""Escalation package builder."""

from __future__ import annotations

from typing import Any

from src.models.schemas import (
    Decision,
    Diagnosis,
    EmployeeSnapshot,
    EscalationPackage,
    Priority,
)


def _format_tool_result(call: dict[str, Any]) -> str:
    name = call.get("tool_name", "unknown")
    success = call.get("success", False)
    output = call.get("output", {})
    data = output.get("data") if isinstance(output, dict) else None
    status = "ok" if success else "failed"

    if not data:
        return f"{name} ({status}): no data"

    if name == "status_check":
        svc = data.get("name") or data.get("service_id", "service")
        health = data.get("health", "unknown")
        desc = data.get("description", "")
        return f"{name} ({status}): {svc} — {health} — {desc[:120]}"

    if name == "history_search":
        records = data.get("records") or []
        if records:
            first = records[0]
            return (
                f"{name} ({status}): {first.get('id', 'record')} — "
                f"{first.get('problem_summary', '')[:100]}"
            )
        return f"{name} ({status}): no matching history"

    if name == "kb_search":
        articles = data.get("articles") or []
        if articles:
            titles = ", ".join(a.get("title", a.get("id", "article")) for a in articles[:2])
            return f"{name} ({status}): {len(articles)} article(s) — {titles}"
        return f"{name} ({status}): no matching articles"

    if name == "user_lookup":
        return f"{name} ({status}): {data.get('name', '')} ({data.get('department', '')})"

    if name == "policy_check":
        return (
            f"{name} ({status}): {data.get('action', '')} — "
            f"can_execute={data.get('agent_can_execute')} "
            f"approval={data.get('approval_required')}"
        )

    snippet = str(data)[:160]
    return f"{name} ({status}): {snippet}"


def _summarize_tool_calls(tool_calls: list[dict[str, Any]]) -> str:
    if not tool_calls:
        return "No tools were invoked."
    return "\n".join(f"- {_format_tool_result(call)}" for call in tool_calls)


def build_escalation_package(
    *,
    issue_summary: str,
    timeline: str,
    employee: dict[str, Any] | None,
    diagnosis: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    attempted_steps: list[str] | None = None,
    priority: Priority = Priority.P2,
    target_team: str = "IT Helpdesk",
    suggested_next_actions: list[str] | None = None,
) -> EscalationPackage:
    emp_snapshot = None
    if employee:
        emp_snapshot = EmployeeSnapshot(
            id=employee.get("id", ""),
            name=employee.get("name", ""),
            email=employee.get("email", ""),
            department=employee.get("department", ""),
            role=employee.get("role", ""),
            location=employee.get("location", ""),
        )

    return EscalationPackage(
        issue_summary=issue_summary,
        timeline=timeline,
        employee=emp_snapshot,
        diagnosis=Diagnosis.model_validate(diagnosis),
        tool_results_summary=_summarize_tool_calls(tool_calls),
        attempted_steps=attempted_steps or [],
        recommended_priority=priority,
        target_team=target_team,
        suggested_next_actions=suggested_next_actions
        or ["Review escalation package", "Contact employee for follow-up"],
    )


def format_escalation_display(package: EscalationPackage) -> str:
    lines = [
        "═══════════════════════════════════════",
        "  ESCALATION PACKAGE",
        "═══════════════════════════════════════",
        f"Priority:    {package.recommended_priority.value}",
        f"Team:        {package.target_team}",
        f"Summary:     {package.issue_summary}",
    ]

    if package.employee:
        emp = package.employee
        lines.append(f"Employee:    {emp.name} ({emp.department}, {emp.role})")

    if package.diagnosis and package.diagnosis.hypothesis:
        lines.extend(["", "Diagnosis:", f"  {package.diagnosis.hypothesis[:200]}"])

    lines.extend(["", "Timeline:"])
    for line in package.timeline.splitlines():
        stripped = line.strip()
        if stripped:
            prefix = "  " if not stripped.startswith("-") else "  "
            lines.append(f"{prefix}{stripped.lstrip('- ')}")

    lines.extend(["", "Tools Checked:"])
    for line in package.tool_results_summary.splitlines():
        lines.append(f"  {line.lstrip('- ')}")

    if package.attempted_steps:
        lines.extend(["", "Attempted:"])
        for step in package.attempted_steps:
            lines.append(f"  - {step}")

    if package.suggested_next_actions:
        lines.extend(["", "Suggested Actions for Human Agent:"])
        for action in package.suggested_next_actions:
            lines.append(f"  - {action}")

    lines.append("═══════════════════════════════════════")
    return "\n".join(lines)


def should_escalate(decision: str | None) -> bool:
    return decision == Decision.ESCALATE.value
