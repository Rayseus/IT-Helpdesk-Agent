"""LangChain tool registry and unified invocation."""

from __future__ import annotations

import json
from typing import Any, Callable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.models.schemas import ToolCallRecord, ToolResponse
from src.tools.base import response_to_dict
from src.tools.history_search import history_search
from src.tools.kb_search import kb_search
from src.tools.policy_check import policy_check
from src.tools.status_check import status_check
from src.tools.user_lookup import user_lookup


class KBSearchInput(BaseModel):
    query: str = Field(description="Search query for IT knowledge base")
    category: str | None = Field(default=None, description="Optional category filter")
    limit: int = Field(default=3, description="Max results")


class StatusCheckInput(BaseModel):
    service_id: str | None = Field(default=None, description="Service ID e.g. okta, salesforce")
    region: str | None = Field(default=None, description="Employee region e.g. Chicago")


class UserLookupInput(BaseModel):
    employee_id: str | None = Field(default=None, description="Employee ID")
    email: str | None = Field(default=None, description="Employee email")


class HistorySearchInput(BaseModel):
    query: str = Field(description="Search query for past resolutions")
    systems: list[str] | None = Field(default=None, description="Filter by systems")
    limit: int = Field(default=5, description="Max results")


class PolicyCheckInput(BaseModel):
    action: str = Field(description="Policy action e.g. grant_snowflake_prod")
    employee_id: str = Field(description="Employee requesting access")
    context: str | None = Field(default=None, description="Optional context")


def _wrap(fn: Callable[..., ToolResponse], tool_name: str) -> Callable[..., str]:
    def runner(**kwargs: Any) -> str:
        result = fn(**kwargs)
        return json.dumps(response_to_dict(result), default=str)

    runner.__name__ = tool_name
    return runner


def get_langchain_tools() -> list[StructuredTool]:
    return [
        StructuredTool.from_function(
            func=_wrap(kb_search, "kb_search"),
            name="kb_search",
            description="Search IT knowledge base articles and runbooks",
            args_schema=KBSearchInput,
        ),
        StructuredTool.from_function(
            func=_wrap(status_check, "status_check"),
            name="status_check",
            description="Check IT service health and known outages",
            args_schema=StatusCheckInput,
        ),
        StructuredTool.from_function(
            func=_wrap(user_lookup, "user_lookup"),
            name="user_lookup",
            description="Look up employee directory info by ID or email",
            args_schema=UserLookupInput,
        ),
        StructuredTool.from_function(
            func=_wrap(history_search, "history_search"),
            name="history_search",
            description="Search historical resolved IT issues",
            args_schema=HistorySearchInput,
        ),
        StructuredTool.from_function(
            func=_wrap(policy_check, "policy_check"),
            name="policy_check",
            description="Check if agent is authorized to perform an action",
            args_schema=PolicyCheckInput,
        ),
    ]


def invoke_tool(name: str, **kwargs: Any) -> ToolResponse:
    dispatch: dict[str, Callable[..., ToolResponse]] = {
        "kb_search": kb_search,
        "status_check": status_check,
        "user_lookup": user_lookup,
        "history_search": history_search,
        "policy_check": policy_check,
    }
    if name not in dispatch:
        return ToolResponse(success=False, tool=name, data=None, error=f"unknown tool: {name}")
    return dispatch[name](**kwargs)


def to_tool_call_record(name: str, kwargs: dict[str, Any], response: ToolResponse) -> ToolCallRecord:
    return ToolCallRecord(
        tool_name=name,
        input=kwargs,
        output=response_to_dict(response),
        success=response.success,
        error=response.error,
    )
