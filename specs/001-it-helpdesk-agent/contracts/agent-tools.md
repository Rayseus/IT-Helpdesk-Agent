# Agent Tools Contract

**Version**: 1.0.0

所有工具返回统一 envelope：

```json
{
  "success": true,
  "tool": "kb_search",
  "data": { ... },
  "error": null
}
```

失败时 `success: false`，`error` 为可读字符串。

---

## kb_search

**Purpose**: 检索 IT 知识库文章

**Input**:
```json
{
  "query": "string (required)",
  "category": "string (optional: password|vpn|software|access|hardware)",
  "limit": "int (optional, default 3)"
}
```

**Output**:
```json
{
  "articles": [
    {
      "id": "kb-okta-reset",
      "title": "Okta Password Reset Runbook",
      "category": "password",
      "tags": ["okta", "password", "mfa"],
      "snippet": "...",
      "relevance_score": 0.92
    }
  ],
  "total_found": 1
}
```

---

## status_check

**Purpose**: 查询 IT 服务健康状态

**Input**:
```json
{
  "service_id": "string (optional, e.g. okta)",
  "region": "string (optional, e.g. Chicago)"
}
```

**Output** (single service):
```json
{
  "service_id": "salesforce",
  "name": "Salesforce CRM",
  "health": "degraded",
  "affected_regions": ["Chicago", "New York"],
  "description": "Intermittent latency since 2026-05-27",
  "eta_resolution": "2026-05-28T18:00:00Z",
  "recent_changes": [...]
}
```

**Output** (no service_id): 返回所有服务摘要列表。

---

## user_lookup

**Purpose**: 查询员工目录信息

**Input** (one of):
```json
{ "employee_id": "emp-001" }
```
```json
{ "email": "jane.doe@company.com" }
```

**Output**:
```json
{
  "id": "emp-001",
  "name": "Jane Doe",
  "email": "jane.doe@company.com",
  "department": "Sales",
  "role": "Account Executive",
  "location": "Chicago",
  "equipment": ["MacBook Pro", "Dock"],
  "permissions": ["salesforce", "okta"],
  "account_status": "active",
  "lock_reason": null
}
```

**Errors**: `employee_not_found`

---

## history_search

**Purpose**: 搜索历史已解决案例

**Input**:
```json
{
  "query": "string (required)",
  "systems": ["string"] ,
  "limit": "int (optional, default 5)"
}
```

**Output**:
```json
{
  "records": [
    {
      "id": "hist-042",
      "problem_summary": "Salesforce slow loading in Chicago",
      "symptoms": ["slow", "timeout"],
      "systems_involved": ["salesforce"],
      "resolution": "Known CDN issue, cleared after 4 hours",
      "resolved_at": "2026-03-15T10:00:00Z"
    }
  ],
  "total_found": 1
}
```

---

## policy_check

**Purpose**: 判定 Agent 是否有权执行某操作

**Input**:
```json
{
  "action": "string (required, e.g. grant_snowflake_prod)",
  "employee_id": "string (required)",
  "context": "string (optional, free-text reason)"
}
```

**Output**:
```json
{
  "action": "grant_snowflake_prod",
  "agent_can_execute": false,
  "approval_required": "manager",
  "conditions": ["Must be Data Engineering role", "Manager approval required"],
  "description": "Production Snowflake access requires manager approval",
  "recommended_escalation_team": "Data Platform"
}
```

---

## Tool Invocation Rules (Agent)

1. 每轮诊断至少调用 1 个工具后再给出结论
2. 权限相关请求 MUST 调用 `policy_check`
3. 性能/连接问题 SHOULD 调用 `status_check` + `kb_search`
4. 账户问题 MUST 调用 `user_lookup` + `kb_search`
5. 工具失败时 MAY 重试 1 次，之后 MUST 告知用户或升级
