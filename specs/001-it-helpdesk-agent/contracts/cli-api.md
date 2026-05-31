# CLI & API Contract

**Version**: 1.0.0

## CLI (Typer)

### `chat`

交互式多轮对话。

```
python -m src.cli.main chat [--employee EMP_ID] [--session SESSION_ID]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--employee` | string | null | 预设员工 ID，跳过身份询问 |
| `--session` | string | auto | 恢复已有会话 |

**Output**: Rich 格式化对话；每次 Agent 回复后显示 `[tools: kb_search, status_check]` 摘要。

### `ask`

单次问答（非交互）。

```
python -m src.cli.main ask "MESSAGE" [--employee EMP_ID]
```

### `tool`

直接调用工具（调试/演示）。

```
python -m src.cli.main tool {kb-search|status|user|history|policy} [OPTIONS]
```

### `eval`

运行评估套件。

```
python -m src.cli.main eval [--scenario NAME] [--verbose]
```

**Exit codes**:
- `0`: 全部通过
- `1`: 有失败场景
- `2`: 配置错误

---

## API (FastAPI, Optional)

### `POST /chat`

**Request**:
```json
{
  "message": "I can't log into Okta",
  "session_id": "uuid (optional)",
  "employee_id": "emp-001 (optional)"
}
```

**Response**:
```json
{
  "session_id": "uuid",
  "reply": "I see you're having trouble with Okta...",
  "decision": "clarify",
  "tools_used": ["user_lookup", "status_check"],
  "escalation_package": null
}
```

### `GET /health`

```json
{ "status": "ok", "llm_provider": "gemini" }
```

### `GET /session/{session_id}`

返回会话状态（调试）。

---

## Escalation Package Display (CLI)

升级时在终端输出：

```
═══════════════════════════════════════
  ESCALATION PACKAGE
═══════════════════════════════════════
Priority:    P1
Team:        IT Helpdesk
Summary:     Okta login failure after password reset

Timeline:
  - User locked out since 09:00
  - Self-service reset attempted, still failing

Tools Checked:
  - user_lookup: account locked (too many MFA attempts)
  - status_check: Okta healthy
  - kb_search: okta-mfa-unlock runbook found

Attempted:
  - Guided password reset steps (user confirms already done)

Suggested Actions for Human Agent:
  - Unlock MFA device binding
  - Verify Okta group membership
═══════════════════════════════════════
```
