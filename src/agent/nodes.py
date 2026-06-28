"""LangGraph node implementations."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.agent.escalation import build_escalation_package
from src.agent.complex_handlers import apply_complex_rules, prefetch_complex_tools
from src.agent.access_handlers import apply_access_rules, prefetch_access_tools
from src.agent.password_handlers import (
    apply_password_account_rules,
    escalation_priority_for_message,
    prefetch_password_tools,
)
from src.agent.software_handlers import (
    apply_software_performance_rules,
    needs_software_clarify,
    prefetch_software_tools,
    software_clarify_questions,
)
from src.agent.vpn_handlers import apply_vpn_rules, prefetch_vpn_tools
from src.agent.prompts import (
    CLARIFY_PROMPT,
    INVESTIGATE_PROMPT,
    RESPOND_PROMPT,
    SYSTEM_PROMPT,
)
from src.agent.state import GraphState, append_message, empty_diagnosis
from src.config import get_settings
from src.logging_config import get_logger
from src.models.schemas import Decision, MessageRole, Priority
from src.tools.registry import get_langchain_tools, invoke_tool, to_tool_call_record

logger = get_logger(__name__)

VAGUE_PATTERNS = [
    r"computer (is )?broken",
    r"nothing works",
    r"help me",
    r"it'?s broken",
]

META_PATTERNS = [
    r"^who are you\b",
    r"^what can you do\b",
    r"^what do you do\b",
    r"^who am i talking to\b",
    r"^introduce yourself\b",
    r"^你是谁",
    r"^你能做什么",
    r"^你是做什么的",
    r"^(hi|hello|hey)\s*[!.]?$",
]

INTRO_REPLY = (
    "I'm your company's IT Helpdesk Agent. I help employees with:\n"
    "- Password and account issues (Okta, MFA, lockouts)\n"
    "- VPN and remote connectivity (GlobalProtect)\n"
    "- Software and application performance\n"
    "- Access and permission requests\n"
    "- Complex multi-system issues (with escalation when needed)\n\n"
    "Please describe the IT issue you're experiencing, and I'll investigate."
)

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "password": ["okta", "password", "login", "mfa", "locked", "account"],
    "software": ["salesforce", "slow", "loading", "application", "app"],
    "vpn": ["vpn", "disconnect", "globalprotect", "remote"],
    "access": ["access", "permission", "snowflake", "grafana", "grant"],
    "complex": ["jenkins", "pipeline", "tableau", "maintenance"],
}


def get_llm():
    settings = get_settings()
    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key or None,
        )
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key or None,
    )


def _kw_hit(keyword: str, text: str) -> bool:
    # Word-boundary match so short keywords (e.g. "app") don't match inside
    # unrelated words like "happens" / "apply".
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def _detect_category(text: str) -> str | None:
    lower = text.lower()
    scores = {
        cat: sum(1 for kw in kws if _kw_hit(kw, lower)) for cat, kws in CATEGORY_KEYWORDS.items()
    }
    if any(w in lower for w in ["jenkins", "pipeline", "tableau"]) and scores.get("complex", 0) > 0:
        return "complex"
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def _is_vague(text: str) -> bool:
    lower = text.lower().strip()
    if any(re.search(p, lower) for p in VAGUE_PATTERNS):
        return True
    return len(lower.split()) <= 4 and lower in {"help", "help me", "help!", "something is wrong"}


def _is_meta_intent(text: str) -> bool:
    """Out-of-scope identity or capability questions (not IT diagnosis)."""
    if _detect_category(text):
        return False
    lower = text.lower().strip()
    return any(re.search(p, lower) for p in META_PATTERNS)


def intake_node(state: GraphState) -> dict[str, Any]:
    user_msg = state.get("last_user_message", "")
    updates: dict[str, Any] = {
        **append_message(state, MessageRole.USER.value, user_msg),
        "turn_count": state.get("turn_count", 0) + 1,
        # Reset per-turn routing so a prior clarify does not stick on the next message.
        "decision": None,
        "pending_questions": [],
        # Reset per-turn tool calls so prior turns don't pollute this turn's
        # display / escalation package (tool_calls has no accumulating reducer).
        "tool_calls": [],
    }

    category = _detect_category(user_msg)
    diagnosis = dict(state.get("diagnosis") or empty_diagnosis())
    if category:
        diagnosis["category"] = category

    updates["diagnosis"] = diagnosis

    if _is_meta_intent(user_msg):
        diagnosis["category"] = "meta"
        updates["diagnosis"] = diagnosis
        updates["decision"] = Decision.RESOLVE.value
        updates["assistant_reply"] = INTRO_REPLY
    elif _is_vague(user_msg):
        updates["decision"] = Decision.CLARIFY.value
        updates["pending_questions"] = [
            "What exactly happens when you try to use it?",
            "When did the issue start, and is it affecting only you or your whole team?",
        ]
    elif category == "software" and needs_software_clarify(user_msg):
        updates["decision"] = Decision.CLARIFY.value
        updates["pending_questions"] = software_clarify_questions()
    return updates


def clarify_node(state: GraphState) -> dict[str, Any]:
    questions = state.get("pending_questions") or [
        "Could you describe the specific error or symptom you're seeing?",
    ]
    reply = (
        "I'd like to help, but I need a bit more detail.\n\n"
        + "\n".join(f"- {q}" for q in questions[:2])
    )
    return {
        **append_message(state, MessageRole.ASSISTANT.value, reply),
        "assistant_reply": reply,
        "decision": Decision.CLARIFY.value,
    }


def _execute_tool_call(name: str, args: dict[str, Any], employee_id: str | None) -> dict[str, Any]:
    if name == "user_lookup" and employee_id and not args.get("employee_id") and not args.get("email"):
        args = {**args, "employee_id": employee_id}
    if name == "policy_check" and employee_id and not args.get("employee_id"):
        args = {**args, "employee_id": employee_id}

    response = invoke_tool(name, **args)
    record = to_tool_call_record(name, args, response)
    return {"record": record.model_dump(mode="json"), "response": response}


def investigate_node(state: GraphState) -> dict[str, Any]:
    """Run LLM with tool calling loop."""
    tools = get_langchain_tools()
    llm = get_llm().bind_tools(tools)

    history = state.get("messages", [])
    lc_messages: list[Any] = [SystemMessage(content=f"{SYSTEM_PROMPT}\n\n{INVESTIGATE_PROMPT}")]
    for msg in history[-10:]:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))

    employee_id = state.get("employee_id")
    new_tool_records: list[dict] = []
    final_response: AIMessage | None = None

    for _ in range(6):
        ai_msg: AIMessage = llm.invoke(lc_messages)
        lc_messages.append(ai_msg)

        if not ai_msg.tool_calls:
            final_response = ai_msg
            break

        for tool_call in ai_msg.tool_calls:
            name = tool_call["name"]
            args = tool_call.get("args") or {}
            executed = _execute_tool_call(name, args, employee_id)
            new_tool_records.append(executed["record"])
            tool_content = json.dumps(executed["response"].model_dump(mode="json"), default=str)
            lc_messages.append(
                ToolMessage(content=tool_content, tool_call_id=tool_call["id"])
            )

    if final_response is None:
        final_response = AIMessage(content="I need to escalate this — unable to complete diagnosis.")

    reply_text = final_response.content or ""
    decision = _infer_decision(reply_text, new_tool_records)

    diagnosis = dict(state.get("diagnosis") or empty_diagnosis())
    diagnosis["hypothesis"] = reply_text[:300]
    diagnosis["confidence"] = 0.75 if new_tool_records else 0.4
    diagnosis["investigated"] = list({r["tool_name"] for r in new_tool_records})

    return {
        "tool_calls": new_tool_records,
        "assistant_reply": reply_text,
        "decision": decision,
        "diagnosis": diagnosis,
    }


def _infer_decision(reply: str, tool_records: list[dict]) -> str:
    lower = reply.lower()
    if any(w in lower for w in ["escalat", "human agent", "it helpdesk will", "requires approval", "manager approval"]):
        return Decision.ESCALATE.value
    if any(w in lower for w in ["could you", "can you tell", "need more", "which", "what error"]):
        return Decision.CLARIFY.value
    if tool_records and any(w in lower for w in ["step 1", "try ", "follow these", "here's how"]):
        return Decision.RESOLVE.value
    return Decision.RESOLVE.value if tool_records else Decision.CLARIFY.value


def decide_node(state: GraphState) -> dict[str, Any]:
    decision = state.get("decision") or Decision.CLARIFY.value
    return {"decision": decision}


def escalate_node(state: GraphState) -> dict[str, Any]:
    employee_id = state.get("employee_id")
    employee_data = None
    if employee_id:
        from src.tools.user_lookup import user_lookup

        result = user_lookup(employee_id=employee_id)
        if result.success:
            employee_data = result.data

    user_msg = state.get("last_user_message", "")
    priority = Priority.P1 if "urgent" in user_msg.lower() else Priority.P2
    target_team = state.get("_escalation_team") or "IT Helpdesk"
    if state.get("_escalation_priority"):
        priority = Priority(state["_escalation_priority"])

    attempted = state.get("_attempted_steps") or [
        "Guided self-service from agent conversation"
    ]

    package = build_escalation_package(
        issue_summary=user_msg[:200],
        timeline=state.get("_escalation_timeline")
        or f"Reported during session {state.get('session_id', 'unknown')}",
        employee=employee_data,
        diagnosis=state.get("diagnosis") or empty_diagnosis(),
        tool_calls=state.get("tool_calls") or [],
        attempted_steps=attempted,
        priority=priority,
        target_team=target_team,
        suggested_next_actions=_suggested_actions_for_escalation(state),
    )

    from src.agent.escalation import format_escalation_display

    display = format_escalation_display(package)
    reply = (state.get("assistant_reply") or "") + "\n\n" + display

    return {
        "escalation_package": package.model_dump(mode="json"),
        **append_message(state, MessageRole.ASSISTANT.value, reply),
        "assistant_reply": reply,
        "decision": Decision.ESCALATE.value,
    }


def respond_node(state: GraphState) -> dict[str, Any]:
    reply = state.get("assistant_reply") or "I've reviewed your issue. Please let me know if you need anything else."
    diagnosis = state.get("diagnosis") or {}

    # Deterministic category paths — skip LLM polish
    if diagnosis.get("category") not in {"password", "software", "vpn", "access", "meta"}:
        llm = get_llm()
        lc_messages = [
            SystemMessage(content=f"{SYSTEM_PROMPT}\n\n{RESPOND_PROMPT}"),
            HumanMessage(content=state.get("last_user_message", "")),
            AIMessage(content=reply),
        ]
        try:
            polished = llm.invoke(lc_messages)
            if polished.content:
                reply = polished.content
        except Exception as exc:
            logger.warning("respond_polish_failed", error=str(exc))

    return {
        **append_message(state, MessageRole.ASSISTANT.value, reply),
        "assistant_reply": reply,
        "decision": state.get("decision") or Decision.RESOLVE.value,
    }


def _suggested_actions_for_escalation(state: GraphState) -> list[str]:
    diagnosis = state.get("diagnosis") or {}
    if diagnosis.get("category") == "password":
        return [
            "Unlock MFA device binding",
            "Verify Okta group membership",
            "Confirm no active Okta outage for employee region",
        ]
    if diagnosis.get("category") == "vpn":
        return [
            "Review VPN client logs and session drops",
            "Verify device certificate and GlobalProtect version",
            "Check for gateway-side session limits or profile issues",
            "Contact employee to confirm post-maintenance behavior",
        ]
    if diagnosis.get("category") == "access":
        return [
            "Verify manager approval for production access requests",
            "Confirm business justification and data scope documented",
            "Process Snowflake prod provisioning after approval",
            "Notify employee when access is active",
        ]
    if diagnosis.get("category") == "complex":
        return [
            "Investigate Jenkins build timeouts and network ACL impact",
            "Verify data pipeline connectivity post-maintenance",
            "Refresh Tableau extracts after pipeline restored",
            "Coordinate with IT on maintenance rollback if needed",
        ]
    return ["Review escalation package", "Contact employee for follow-up"]


def route_after_intake(state: GraphState) -> str:
    if state.get("decision") == Decision.CLARIFY.value:
        return "clarify"
    diagnosis = state.get("diagnosis") or {}
    category = diagnosis.get("category")
    if category == "meta":
        return "respond"
    if category == "password":
        return "investigate_password"
    if category == "software":
        return "investigate_software"
    if category == "vpn":
        return "investigate_vpn"
    if category == "access":
        return "investigate_access"
    if category == "complex":
        return "investigate_complex"
    return "investigate"


def investigate_password_node(state: GraphState) -> dict[str, Any]:
    """Deterministic password/account flow with mandatory tool prefetch (US1)."""
    employee_id = state.get("employee_id")
    user_msg = state.get("last_user_message", "")
    tool_records = prefetch_password_tools(employee_id, user_msg)
    decision, reply, target_team = apply_password_account_rules(tool_records, user_msg)

    diagnosis = dict(state.get("diagnosis") or empty_diagnosis())
    diagnosis["category"] = "password"
    diagnosis["hypothesis"] = reply[:300]
    diagnosis["confidence"] = 0.9 if tool_records else 0.5
    diagnosis["investigated"] = [r["tool_name"] for r in tool_records]

    updates: dict[str, Any] = {
        "tool_calls": tool_records,
        "assistant_reply": reply,
        "decision": decision,
        "diagnosis": diagnosis,
    }

    if decision == Decision.ESCALATE.value:
        updates["_escalation_team"] = target_team or "IT Helpdesk"
        updates["_escalation_priority"] = escalation_priority_for_message(user_msg).value

    return updates


def investigate_software_node(state: GraphState) -> dict[str, Any]:
    """Deterministic software/performance flow with mandatory tool prefetch (US2)."""
    employee_id = state.get("employee_id")
    user_msg = state.get("last_user_message", "")
    tool_records = prefetch_software_tools(employee_id, user_msg)
    decision, reply, _target = apply_software_performance_rules(tool_records, user_msg)

    diagnosis = dict(state.get("diagnosis") or empty_diagnosis())
    diagnosis["category"] = "software"
    diagnosis["hypothesis"] = reply[:300]
    diagnosis["confidence"] = 0.9 if tool_records else 0.5
    diagnosis["investigated"] = [r["tool_name"] for r in tool_records]

    return {
        "tool_calls": tool_records,
        "assistant_reply": reply,
        "decision": decision,
        "diagnosis": diagnosis,
    }


def investigate_vpn_node(state: GraphState) -> dict[str, Any]:
    """Deterministic VPN/connectivity flow with mandatory tool prefetch (US3)."""
    employee_id = state.get("employee_id")
    user_msg = state.get("last_user_message", "")
    tool_records = prefetch_vpn_tools(employee_id, user_msg)
    decision, reply, target_team, attempted_steps = apply_vpn_rules(tool_records, user_msg)

    diagnosis = dict(state.get("diagnosis") or empty_diagnosis())
    diagnosis["category"] = "vpn"
    diagnosis["hypothesis"] = reply[:300]
    diagnosis["confidence"] = 0.9 if tool_records else 0.5
    diagnosis["investigated"] = [r["tool_name"] for r in tool_records]

    updates: dict[str, Any] = {
        "tool_calls": tool_records,
        "assistant_reply": reply,
        "decision": decision,
        "diagnosis": diagnosis,
    }

    if decision == Decision.ESCALATE.value:
        updates["_escalation_team"] = target_team or "Network / VPN Team"
        updates["_escalation_priority"] = Priority.P2.value
        updates["_attempted_steps"] = attempted_steps

    return updates


def investigate_access_node(state: GraphState) -> dict[str, Any]:
    """Deterministic access/permissions flow with policy checks (US4)."""
    employee_id = state.get("employee_id")
    user_msg = state.get("last_user_message", "")
    tool_records, actions = prefetch_access_tools(employee_id, user_msg)
    decision, reply, target_team, attempted_steps = apply_access_rules(
        tool_records, user_msg, actions
    )

    diagnosis = dict(state.get("diagnosis") or empty_diagnosis())
    diagnosis["category"] = "access"
    diagnosis["hypothesis"] = reply[:300]
    diagnosis["confidence"] = 0.9 if tool_records else 0.5
    diagnosis["investigated"] = [r["tool_name"] for r in tool_records]
    diagnosis["requested_actions"] = actions

    updates: dict[str, Any] = {
        "tool_calls": tool_records,
        "assistant_reply": reply,
        "decision": decision,
        "diagnosis": diagnosis,
    }

    if decision == Decision.ESCALATE.value:
        updates["_escalation_team"] = target_team or "Data Platform"
        updates["_escalation_priority"] = Priority.P2.value
        updates["_attempted_steps"] = attempted_steps

    return updates


def investigate_complex_node(state: GraphState) -> dict[str, Any]:
    """Deterministic multi-system pipeline failure flow (US5)."""
    employee_id = state.get("employee_id")
    user_msg = state.get("last_user_message", "")
    tool_records, systems = prefetch_complex_tools(employee_id, user_msg)
    decision, reply, target_team, attempted_steps, timeline, priority = apply_complex_rules(
        tool_records, user_msg
    )

    diagnosis = dict(state.get("diagnosis") or empty_diagnosis())
    diagnosis["category"] = "complex"
    diagnosis["hypothesis"] = reply[:300]
    diagnosis["confidence"] = 0.95 if tool_records else 0.5
    diagnosis["investigated"] = [r["tool_name"] for r in tool_records]
    diagnosis["systems"] = systems

    return {
        "tool_calls": tool_records,
        "assistant_reply": reply,
        "decision": decision,
        "diagnosis": diagnosis,
        "_escalation_team": target_team,
        "_escalation_priority": priority,
        "_escalation_timeline": timeline,
        "_attempted_steps": attempted_steps,
    }


def route_after_investigate(state: GraphState) -> str:
    decision = state.get("decision")
    if decision == Decision.ESCALATE.value:
        return "escalate"
    if decision == Decision.CLARIFY.value:
        return "clarify"
    return "respond"
