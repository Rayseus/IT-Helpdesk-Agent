"""Smoke tests for project setup (Phase 1)."""

import pytest


@pytest.mark.unit
def test_python_version():
    import sys

    assert sys.version_info >= (3, 12)


@pytest.mark.unit
def test_package_imports():
    import src
    import src.agent
    import src.tools
    import src.models
    import src.cli

    assert src.__doc__
