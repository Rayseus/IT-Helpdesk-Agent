"""Pytest wrapper for YAML eval scenarios."""

from __future__ import annotations

import pytest

from tests.eval.runner import load_scenarios, run_scenario

ALL_SCENARIOS = load_scenarios(pattern="*.yaml")


@pytest.mark.eval
@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda s: s.name)
def test_eval_scenario(scenario):
    result = run_scenario(scenario)
    assert result.passed, "; ".join(result.errors)
