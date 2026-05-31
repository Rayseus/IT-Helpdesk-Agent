"""Typer CLI for IT Helpdesk Agent."""

from __future__ import annotations

import json
import sys
import uuid
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from src.agent.escalation import format_escalation_display
from src.agent.graph import run_turn
from src.agent.state import GraphState, make_initial_state
from src.config import get_settings
from src.logging_config import configure_logging
from src.models.schemas import EscalationPackage
from src.tools.history_search import history_search
from src.tools.kb_search import kb_search
from src.tools.policy_check import policy_check
from src.tools.status_check import status_check
from src.tools.user_lookup import user_lookup

app = typer.Typer(no_args_is_help=True, help="IT Helpdesk Agent CLI")
tool_app = typer.Typer(help="Invoke backend tools directly")
app.add_typer(tool_app, name="tool")

console = Console()
_sessions: dict[str, GraphState] = {}


def _tool_names(state: GraphState) -> list[str]:
    calls = state.get("tool_calls") or []
    return list(dict.fromkeys(c.get("tool_name", "") for c in calls if c.get("tool_name")))


def _print_escalation_package(state: GraphState) -> None:
    raw = state.get("escalation_package")
    if not raw:
        return
    package = EscalationPackage.model_validate(raw)
    console.print(
        Panel(
            format_escalation_display(package),
            title="[bold yellow]Escalation Package[/bold yellow]",
            border_style="yellow",
        )
    )


def _print_agent_response(state: GraphState) -> None:
    reply = state.get("assistant_reply") or ""
    decision = state.get("decision") or "unknown"
    tools = _tool_names(state)

    # Show narrative reply without duplicating escalation block when package exists
    display_reply = reply
    if state.get("escalation_package") and "ESCALATION PACKAGE" in reply:
        display_reply = reply.split("═══════════════════════════════════════")[0].strip()

    console.print(Panel(Markdown(display_reply), title="[bold green]Agent[/bold green]", border_style="green"))
    console.print(f"[dim]decision:[/dim] {decision}  [dim]tools:[/dim] {', '.join(tools) or 'none'}")
    _print_escalation_package(state)


@app.command()
def chat(
    employee: Optional[str] = typer.Option(None, "--employee", "-e", help="Employee ID"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID to resume"),
) -> None:
    """Interactive multi-turn IT support chat."""
    configure_logging()
    session_id = session or str(uuid.uuid4())
    state = _sessions.get(session_id) or make_initial_state(session_id, employee)
    if employee:
        state = {**state, "employee_id": employee}

    console.print(Panel(
        f"Session: [cyan]{session_id}[/cyan]\nEmployee: [cyan]{state.get('employee_id') or 'not set'}[/cyan]\n"
        "Type your IT issue (Ctrl+C or 'exit' to quit)",
        title="IT Helpdesk Agent",
    ))

    try:
        while True:
            user_input = console.input("[bold blue]You:[/bold blue] ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "q"}:
                break
            state = run_turn(user_input, state=state)
            _sessions[session_id] = state
            _print_agent_response(state)
    except KeyboardInterrupt:
        console.print("\n[dim]Session ended.[/dim]")


@app.command()
def ask(
    message: str = typer.Argument(..., help="IT issue description"),
    employee: Optional[str] = typer.Option(None, "--employee", "-e", help="Employee ID"),
) -> None:
    """Single-turn question (non-interactive)."""
    configure_logging()
    state = run_turn(message, employee_id=employee)
    _print_agent_response(state)


@tool_app.command("kb-search")
def tool_kb_search(
    query: str = typer.Option(..., "--query", "-q"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    limit: int = typer.Option(3, "--limit", "-n"),
) -> None:
    result = kb_search(query, category=category, limit=limit)
    console.print_json(json.dumps(result.model_dump(mode="json"), default=str))


@tool_app.command("status")
def tool_status(
    service: Optional[str] = typer.Option(None, "--service", "-s"),
    region: Optional[str] = typer.Option(None, "--region", "-r"),
) -> None:
    result = status_check(service_id=service, region=region)
    console.print_json(json.dumps(result.model_dump(mode="json"), default=str))


@tool_app.command("user")
def tool_user(
    employee_id: Optional[str] = typer.Option(None, "--id"),
    email: Optional[str] = typer.Option(None, "--email"),
) -> None:
    result = user_lookup(employee_id=employee_id, email=email)
    console.print_json(json.dumps(result.model_dump(mode="json"), default=str))


@tool_app.command("history")
def tool_history(
    query: str = typer.Option(..., "--query", "-q"),
    limit: int = typer.Option(5, "--limit", "-n"),
) -> None:
    result = history_search(query, limit=limit)
    console.print_json(json.dumps(result.model_dump(mode="json"), default=str))


@tool_app.command("policy")
def tool_policy(
    action: str = typer.Option(..., "--action", "-a"),
    employee_id: str = typer.Option("emp-002", "--employee", "-e"),
    context: Optional[str] = typer.Option(None, "--context"),
) -> None:
    result = policy_check(action=action, employee_id=employee_id, context=context)
    console.print_json(json.dumps(result.model_dump(mode="json"), default=str))


@app.command("eval")
def eval_command(
    scenario: Optional[str] = typer.Option(None, "--scenario", "-k", help="Filter by scenario name"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all scenario details"),
) -> None:
    """Run YAML evaluation scenarios (decision, tools, must_contain assertions)."""
    configure_logging()
    from tests.eval.runner import format_results, run_eval_suite

    results = run_eval_suite(name_filter=scenario)
    console.print(format_results(results, verbose=verbose))
    failed = sum(1 for r in results if not r.passed)
    if failed:
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
