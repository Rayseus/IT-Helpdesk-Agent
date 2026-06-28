"""Pydantic entity schemas for IT Helpdesk Agent."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AccountStatus(str, Enum):
    ACTIVE = "active"
    LOCKED = "locked"
    SUSPENDED = "suspended"


class KBCategory(str, Enum):
    PASSWORD = "password"
    VPN = "vpn"
    SOFTWARE = "software"
    ACCESS = "access"
    HARDWARE = "hardware"


class ServiceHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OUTAGE = "outage"
    MAINTENANCE = "maintenance"


class ApprovalRequired(str, Enum):
    NONE = "none"
    MANAGER = "manager"
    SECURITY = "security"
    IT_ADMIN = "it_admin"


class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Decision(str, Enum):
    CLARIFY = "clarify"
    RESOLVE = "resolve"
    ESCALATE = "escalate"


class Employee(BaseModel):
    id: str
    name: str
    email: str
    department: str
    role: str
    location: str
    manager_id: str | None = None
    equipment: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    account_status: AccountStatus = AccountStatus.ACTIVE
    lock_reason: str | None = None

    @field_validator("email")
    @classmethod
    def validate_company_email(cls, v: str) -> str:
        if not v.endswith("@company.com"):
            raise ValueError("email must use @company.com domain")
        return v


class EmployeeSnapshot(BaseModel):
    id: str
    name: str
    email: str
    department: str
    role: str
    location: str


class KnowledgeArticle(BaseModel):
    id: str
    title: str
    category: KBCategory
    tags: list[str] = Field(default_factory=list)
    content: str
    last_updated: date | None = None


class ChangeEvent(BaseModel):
    timestamp: datetime
    description: str
    impact: str


class ServiceStatus(BaseModel):
    service_id: str
    name: str
    health: ServiceHealth
    affected_regions: list[str] = Field(default_factory=list)
    description: str = ""
    eta_resolution: datetime | None = None
    recent_changes: list[ChangeEvent] = Field(default_factory=list)


class ResolutionRecord(BaseModel):
    id: str
    problem_summary: str
    symptoms: list[str] = Field(default_factory=list)
    systems_involved: list[str] = Field(default_factory=list)
    resolution: str
    resolved_at: datetime
    category: str = ""


class PolicyRule(BaseModel):
    id: str
    action: str
    agent_can_execute: bool
    approval_required: ApprovalRequired = ApprovalRequired.NONE
    conditions: list[str] = Field(default_factory=list)
    description: str = ""
    recommended_escalation_team: str = "IT Helpdesk"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Message(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=_utcnow)


class Diagnosis(BaseModel):
    hypothesis: str = ""
    confidence: float = 0.0
    category: str | None = None
    investigated: list[str] = Field(default_factory=list)
    remaining: list[str] = Field(default_factory=list)
    systems: list[str] = Field(default_factory=list)
    requested_actions: list[str] = Field(default_factory=list)


class ToolCallRecord(BaseModel):
    tool_name: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utcnow)
    success: bool = True
    error: str | None = None


class EscalationPackage(BaseModel):
    issue_summary: str
    timeline: str
    employee: EmployeeSnapshot | None = None
    diagnosis: Diagnosis | None = None
    tool_results_summary: str = ""
    attempted_steps: list[str] = Field(default_factory=list)
    recommended_priority: Priority = Priority.P2
    target_team: str = "IT Helpdesk"
    suggested_next_actions: list[str] = Field(default_factory=list)


class ToolResponse(BaseModel):
    success: bool
    tool: str
    data: dict[str, Any] | None = None
    error: str | None = None


class ConversationState(BaseModel):
    """Runtime session state (also used as LangGraph state dict basis)."""

    session_id: str
    employee_id: str | None = None
    messages: list[Message] = Field(default_factory=list)
    diagnosis: Diagnosis = Field(default_factory=Diagnosis)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    pending_questions: list[str] = Field(default_factory=list)
    decision: Decision | None = None
    escalation_package: EscalationPackage | None = None
    turn_count: int = 0

    def to_graph_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_graph_dict(cls, data: dict[str, Any]) -> ConversationState:
        return cls.model_validate(data)
