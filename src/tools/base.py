"""Shared tool utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.models.schemas import ToolResponse


def ok(tool: str, data: dict[str, Any]) -> ToolResponse:
    return ToolResponse(success=True, tool=tool, data=data, error=None)


def fail(tool: str, error: str) -> ToolResponse:
    return ToolResponse(success=False, tool=tool, data=None, error=error)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def response_to_dict(response: ToolResponse) -> dict[str, Any]:
    return response.model_dump(mode="json")
