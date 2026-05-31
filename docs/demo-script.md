# Demo 演示脚本

**依据**：[`agentic_ai_take_home_candidate_instructions_v20260421_01.html`](../agentic_ai_take_home_candidate_instructions_v20260421_01.html)  
**预计时长**：15–20 分钟（核心 8 个 Case）  
**启动命令**：

```bash
# 交互式多轮
python -m src.cli.main chat --employee emp-001

# 单次问答（每轮独立 session，更稳定）
python -m src.cli.main ask "<问题>" --employee emp-001
```

> **说明**：核心 Case 1–8 走确定性 handler，**无需 Gemini API Key**。Bonus Case 同理。现场即兴新问题可能走 LLM 路径，建议 `.env` 中配置 `GEMINI_API_KEY` 作备份。

---

## 演示前准备

| 员工 ID | 角色 | 用途 |
|---------|------|------|
| `emp-001` | Jane Doe，Sales，Chicago | 多数 resolve / clarify 场景 |
| `emp-002` | Alex Chen，Data Engineering，Remote | 权限、多系统故障 |
| `emp-locked` | Sam Rivera，账户锁定 | Okta 升级场景 |

收尾验证：

```bash
python -m src.cli.main eval
```

---

## 推荐演示顺序（15 分钟）

```text
1. [2 min] 架构：LangGraph intake → 分类 handler → resolve / clarify / escalate
2. [6 min] Case 1 → 3 → 4（resolve 三连，展示工具调用）
3. [3 min] Case 2 或 6（展开 Escalation Package）
4. [2 min] Case 5 或 8（策略边界）
5. [1 min] Case 7（clarify，不瞎猜）
6. [1 min] python -m src.cli.main eval → 17/17 passed
```

演示时关注终端输出的 `decision:` 与 `tools:` 行。

---

## 核心 Case（8 个）

覆盖 take-home 文档要求的 5 类场景、工具调用、resolve/escalate 边界、clarify 与策略护栏。

### Case 1 — Okta 密码重置无效（resolve）

| 项 | 内容 |
|----|------|
| **覆盖** | US1 密码/账户；多工具推理 |
| **员工** | `emp-001` |
| **输入** | `I can't log into Okta. I've tried resetting my password but it still doesn't work. I need access urgently for a client meeting in 30 minutes.` |
| **预期** | `decision=resolve` |
| **工具** | `user_lookup`, `kb_search`, `status_check` |
| **演示要点** | 基于 KB runbook 给出分步指引；引用工具结果，不编造文章 |

```bash
python -m src.cli.main ask "I can't log into Okta. I've tried resetting my password but it still doesn't work. I need access urgently for a client meeting in 30 minutes." --employee emp-001
```

---

### Case 2 — Okta 账户锁定（escalate）

| 项 | 内容 |
|----|------|
| **覆盖** | US1 升级边界；Escalation Package |
| **员工** | `emp-locked` |
| **输入** | `I can't log into Okta after resetting my password. I need access urgently for a meeting in 30 minutes.` |
| **预期** | `decision=escalate` |
| **工具** | `user_lookup`, `kb_search`, `status_check` |
| **演示要点** | 识别 **locked**；说明自助重置无效；展示结构化升级包（含 P1 urgency） |

```bash
python -m src.cli.main ask "I can't log into Okta after resetting my password. I need access urgently for a meeting in 30 minutes." --employee emp-locked
```

---

### Case 3 — Salesforce 区域性故障（resolve）

| 项 | 内容 |
|----|------|
| **覆盖** | US2 软件/性能；多源推理（用户位置 + 系统状态） |
| **员工** | `emp-001` |
| **输入** | `Salesforce has been loading extremely slowly since yesterday. My teammates in the Chicago office are seeing the same thing.` |
| **预期** | `decision=resolve` |
| **工具** | `user_lookup`, `status_check`, `kb_search`, `history_search` |
| **演示要点** | 关联 Chicago + **degraded** 状态；给出 ETA；**无需升级** |

```bash
python -m src.cli.main ask "Salesforce has been loading extremely slowly since yesterday. My teammates in the Chicago office are seeing the same thing." --employee emp-001
```

---

### Case 4 — VPN 频繁断连（resolve）

| 项 | 内容 |
|----|------|
| **覆盖** | US3 连接/VPN；KB runbook |
| **员工** | `emp-001` |
| **输入** | `My VPN keeps disconnecting every 10–15 minutes. I'm working remotely and can't access internal tools.` |
| **预期** | `decision=resolve` |
| **工具** | `user_lookup`, `status_check`, `kb_search` |
| **演示要点** | 查询 VPN 网关状态（维护窗口或 healthy）；展示完整 KB 排查步骤 |

```bash
python -m src.cli.main ask "My VPN keeps disconnecting every 10–15 minutes. I'm working remotely and can't access internal tools." --employee emp-001
```

---

### Case 5 — 新员工混合权限申请（escalate + 部分 resolve）

| 项 | 内容 |
|----|------|
| **覆盖** | US4 权限/策略引擎 |
| **员工** | `emp-002` |
| **输入** | `I just joined the Data Engineering team and need access to the Snowflake production database and the internal Grafana dashboards.` |
| **预期** | `decision=escalate`（Snowflake prod 需审批） |
| **工具** | `user_lookup`, `policy_check` |
| **演示要点** | Grafana 可模拟自助开通；Snowflake prod 需经理审批；同一请求内混合决策 |

```bash
python -m src.cli.main ask "I just joined the Data Engineering team and need access to the Snowflake production database and the internal Grafana dashboards." --employee emp-002
```

---

### Case 6 — 多系统管道故障（escalate）

| 项 | 内容 |
|----|------|
| **覆盖** | US5 复杂/多系统；历史案例 + 多服务状态 |
| **员工** | `emp-002` |
| **输入** | `Since the IT maintenance window last Friday, our team's automated data pipeline has been failing. The Jenkins jobs time out and the downstream Tableau reports are stale.` |
| **预期** | `decision=escalate` |
| **工具** | `user_lookup`, `status_check`, `history_search` |
| **演示要点** | 汇总 Jenkins / Tableau 状态；升级至 **Data Platform**；展示完整 Escalation Package |

```bash
python -m src.cli.main ask "Since the IT maintenance window last Friday, our team's automated data pipeline has been failing. The Jenkins jobs time out and the downstream Tableau reports are stale." --employee emp-002
```

---

### Case 7 — 模糊描述（clarify）

| 项 | 内容 |
|----|------|
| **覆盖** | 可靠性；对话式诊断；不幻觉 |
| **员工** | `emp-001` |
| **输入** | `My computer is broken. Help me.` |
| **预期** | `decision=clarify` |
| **工具** | 无 |
| **演示要点** | **不猜测**具体故障；主动追问症状、影响范围 |

```bash
python -m src.cli.main ask "My computer is broken. Help me." --employee emp-001
```

**多轮延续**（同一 `chat` session，展示 state / memory）：

```text
You: My computer is broken. Help me.
Agent: [clarify]

You: GlobalProtect VPN disconnects frequently when I'm on Wi-Fi at home.
Agent: [resolve — VPN runbook + 工具调用]
```

---

### Case 8 — 角色不匹配权限拒绝（resolve / 策略拒绝）

| 项 | 内容 |
|----|------|
| **覆盖** | 安全 / 护栏；策略边界 |
| **员工** | `emp-001`（Sales） |
| **输入** | `Please grant me access to the Snowflake production database for reporting.` |
| **预期** | `decision=resolve`（拒绝并解释，非 escalate） |
| **工具** | `user_lookup`, `policy_check` |
| **演示要点** | Sales 角色 **not eligible**；不模拟开通 prod 权限 |

```bash
python -m src.cli.main ask "Please grant me access to the Snowflake production database for reporting." --employee emp-001
```

---

## Take-Home 考察维度对照

| 文档要求 | 对应 Case |
|----------|-----------|
| 5 类核心场景（题目原文） | Case 1–6 |
| 多轮对话 + 状态记忆 | Case 7 多轮延续 |
| 5 类 Mock 数据源工具调用 | Case 1–6 |
| resolve vs escalate 边界 | Case 1、3、4 resolve；Case 2、5、6 escalate；Case 8 策略拒绝 |
| 不幻觉、有护栏 | Case 7、8 |
| 评估可重复 | `python -m src.cli.main eval` |

---

## Bonus Case（可选加分）

> 时间充裕或面试官追问时使用。与核心 Case 功能有重叠，但侧重不同分支。

### Bonus A — Salesforce 信息不足（clarify）

| 项 | 内容 |
|----|------|
| **员工** | `emp-001` |
| **输入** | `Salesforce is really slow today.` |
| **预期** | `decision=clarify` |
| **演示要点** | 追问是否仅你受影响，或全办公室/队友同样慢 |

```bash
python -m src.cli.main ask "Salesforce is really slow today." --employee emp-001
```

---

### Bonus B — Salesforce 仅个人慢（resolve / 个人排查）

| 项 | 内容 |
|----|------|
| **员工** | `emp-001` |
| **输入** | `Salesforce is extremely slow but only on my laptop. Only me — teammates are fine.` |
| **预期** | `decision=resolve` |
| **演示要点** | 区分个人问题 vs 区域性 outage；给出浏览器/缓存排查步骤 |

```bash
python -m src.cli.main ask "Salesforce is extremely slow but only on my laptop. Only me — teammates are fine." --employee emp-001
```

---

### Bonus C — Grafana 只读自助开通（resolve）

| 项 | 内容 |
|----|------|
| **员工** | `emp-002` |
| **输入** | `I need read-only access to internal Grafana dashboards for my onboarding.` |
| **预期** | `decision=resolve` |
| **演示要点** | Data Eng 角色 + Grafana read-only 策略允许；模拟开通确认 |

```bash
python -m src.cli.main ask "I need read-only access to internal Grafana dashboards for my onboarding." --employee emp-002
```

---

### Bonus D — Admin 越权请求（escalate）

| 项 | 内容 |
|----|------|
| **员工** | `emp-002` |
| **输入** | `I need admin root access to modify production system permissions.` |
| **预期** | `decision=escalate` |
| **演示要点** | Agent **永不**自动开通 admin；升级至安全/IT 团队 |

```bash
python -m src.cli.main ask "I need admin root access to modify production system permissions." --employee emp-002
```

---

### Bonus E — VPN 排查后仍失败（escalate）

| 项 | 内容 |
|----|------|
| **员工** | `emp-001` |
| **方式** | 多轮 `chat` |
| **输入** | 第一轮：`GlobalProtect VPN disconnects frequently when I'm on Wi-Fi at home.` |
| | 第二轮：`I tried everything — updated the client, rebooted router, still disconnecting every 15 minutes.` |
| **预期** | 第一轮 `resolve`；第二轮 `escalate` |
| **演示要点** | 自助步骤无效后升级；附带完整诊断摘要 |

```bash
python -m src.cli.main chat --employee emp-001
```

---

### Bonus F — VPN 维护窗口场景（resolve）

| 项 | 内容 |
|----|------|
| **员工** | `emp-001` |
| **输入** | `My VPN keeps disconnecting every 15 minutes. I can't access internal tools while working remotely.` |
| **预期** | `decision=resolve`（提及 **maintenance**） |
| **演示要点** | 与 Case 4 类似，Mock 数据下更强调维护窗口 + 临时替代方案 |

```bash
python -m src.cli.main ask "My VPN keeps disconnecting every 15 minutes. I can't access internal tools while working remotely." --employee emp-001
```

---

### Bonus G — 未知员工 ID（工具失败容错）

| 项 | 内容 |
|----|------|
| **员工** | 不存在的 ID，或不传 `--employee` |
| **输入** | `I can't log into Okta. Password reset didn't work.` |
| **预期** | 仍给出 Okta 相关指引，不因 `user_lookup` 失败而崩溃 |
| **演示要点** | 工具失败时的 graceful degradation |

```bash
python -m src.cli.main ask "I can't log into Okta. Password reset didn't work."
```

---

## 注意事项

1. 每个 Case 换 persona 时使用对应 `--employee`，或在 `chat` 中重新启动 session。
2. 若曾输入模糊问题导致异常，退出 `chat` 后重新进入（参见 [`bugfix-clarify-state-sticky.md`](./bugfix-clarify-state-sticky.md)）。
3. 评估场景与本文 Case 一一对应，见 `tests/eval/scenarios/*.yaml`。
