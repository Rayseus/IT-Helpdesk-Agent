"""YAML evaluation scenario runner for IT Helpdesk Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.agent.graph import run_turn

SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


@dataclass
class EvalScenario:
    name: str
    description: str = ""
    user_persona: str | None = None
    turns: list[str] = field(default_factory=list)
    expected_decision: str = "resolve"
    expected_tools: list[str] = field(default_factory=list)
    must_contain: list[str] = field(default_factory=list)
    must_not_contain: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    scenario: EvalScenario
    passed: bool
    errors: list[str] = field(default_factory=list)
    decision: str | None = None
    tools_used: list[str] = field(default_factory=list)


def load_scenarios(
    *,
    directory: Path | None = None,
    pattern: str = "*.yaml",
    name_filter: str | None = None,
) -> list[EvalScenario]:
    base = directory or SCENARIOS_DIR
    scenarios: list[EvalScenario] = []
    for path in sorted(base.glob(pattern)):
        text = path.read_text(encoding="utf-8")
        for doc in yaml.safe_load_all(text):
            if not doc:
                continue
            scenario = EvalScenario(
                name=doc["name"],
                description=doc.get("description", ""),
                user_persona=doc.get("user_persona"),
                turns=list(doc.get("turns") or []),
                expected_decision=doc.get("expected_decision", "resolve"),
                expected_tools=list(doc.get("expected_tools") or []),
                must_contain=list(doc.get("must_contain") or []),
                must_not_contain=list(doc.get("must_not_contain") or []),
            )
            if name_filter and name_filter.lower() not in scenario.name.lower():
                continue
            scenarios.append(scenario)
    return scenarios


def _tool_names(state: dict) -> set[str]:
    return {c.get("tool_name") for c in state.get("tool_calls", []) if c.get("tool_name")}


def run_scenario(scenario: EvalScenario) -> EvalResult:
    """Execute a scenario and return pass/fail with assertion errors."""
    errors: list[str] = []
    state: dict = {}

    if not scenario.turns:
        return EvalResult(
            scenario=scenario,
            passed=False,
            errors=["scenario has no turns"],
        )

    for turn in scenario.turns:
        state = run_turn(turn, employee_id=scenario.user_persona, state=state or None)

    decision = state.get("decision")
    tools = sorted(_tool_names(state))
    reply = (state.get("assistant_reply") or "").lower()

    if decision != scenario.expected_decision:
        errors.append(f"decision: expected {scenario.expected_decision!r}, got {decision!r}")

    for expected_tool in scenario.expected_tools:
        if expected_tool not in tools:
            errors.append(f"missing tool {expected_tool!r}, got {tools}")

    for phrase in scenario.must_contain:
        if phrase.lower() not in reply:
            errors.append(f"reply must contain {phrase!r}")

    for phrase in scenario.must_not_contain:
        if phrase.lower() in reply:
            errors.append(f"reply must not contain {phrase!r}")

    return EvalResult(
        scenario=scenario,
        passed=len(errors) == 0,
        errors=errors,
        decision=decision,
        tools_used=tools,
    )


def run_eval_suite(
    *,
    name_filter: str | None = None,
    patterns: list[str] | None = None,
) -> list[EvalResult]:
    """Run all matching YAML scenarios."""
    globs = patterns or ["us*.yaml", "edge_*.yaml"]
    all_scenarios: list[EvalScenario] = []
    seen: set[str] = set()
    for pattern in globs:
        for scenario in load_scenarios(pattern=pattern, name_filter=name_filter):
            if scenario.name in seen:
                continue
            seen.add(scenario.name)
            all_scenarios.append(scenario)

    return [run_scenario(s) for s in all_scenarios]


def format_results(results: list[EvalResult], *, verbose: bool = False) -> str:
    lines: list[str] = []
    passed = sum(1 for r in results if r.passed)
    lines.append(f"Eval: {passed}/{len(results)} passed")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"  [{status}] {result.scenario.name}")
        if verbose or not result.passed:
            if result.scenario.description:
                lines.append(f"         {result.scenario.description}")
            if result.decision is not None:
                lines.append(f"         decision={result.decision} tools={result.tools_used}")
            for err in result.errors:
                lines.append(f"         ! {err}")
    return "\n".join(lines)
