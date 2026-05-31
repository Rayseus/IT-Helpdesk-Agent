# Feature Specification: IT Helpdesk Agent

**Feature Branch**: `001-it-helpdesk-agent`

**Created**: 2026-05-28

**Status**: Draft

**Input**: Agentic AI Take-Home — 构建 AI 驱动的 IT 支持 Agent，替代传统工单系统，使员工通过对话直接获得 IT 问题解决或无缝升级人工。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 密码/账户问题快速恢复 (Priority: P1)

员工无法登录 Okta，已尝试自助重置密码仍失败，且 30 分钟内有客户会议需要紧急访问。

**Why this priority**: 密码/账户问题是最高频 IT 请求，直接体现 Agent 能否在分钟级替代工单队列。

**Independent Test**: 输入 Okta 登录失败场景，Agent 应查询用户目录确认账户状态、检索 KB 中的密码重置 runbook、检查 Okta 系统状态，给出分步修复指引或判定需人工介入。

**Acceptance Scenarios**:

1. **Given** 员工描述 Okta 登录失败且已重置密码无效, **When** Agent 完成诊断, **Then** Agent 提供基于 KB 的具体修复步骤或明确升级并附 urgency 说明
2. **Given** 系统状态显示 Okta 已知 outage, **When** Agent 查询状态, **Then** Agent 告知已知故障、预计恢复时间，并给出临时替代方案（如 VPN 直连）
3. **Given** 用户账户被锁定, **When** Agent 查询用户目录, **Then** Agent 说明锁定原因并告知是否可自助解锁或需 IT 审批

---

### User Story 2 - 软件/应用性能问题诊断 (Priority: P1)

员工报告 Salesforce 自昨天起加载极慢，同办公室同事也有相同问题。

**Why this priority**: 演示多源推理——区分个人问题 vs. 区域性/全局 outage，是 Agent 核心能力。

**Independent Test**: 输入 Salesforce 慢速场景，Agent 应检查系统状态、比对用户位置/部门、检索历史类似案例，判断是否为已知 outage 或需进一步排查。

**Acceptance Scenarios**:

1. **Given** 系统状态有 Salesforce degraded 记录且影响 Chicago 办公室, **When** Agent 确认用户位于 Chicago, **Then** Agent 解释已知问题并给出 ETA，无需升级
2. **Given** 无已知 outage 且仅该用户受影响, **When** Agent 完成诊断, **Then** Agent 提供个性化排查步骤（缓存清理、浏览器检查等）
3. **Given** 信息不足以判断, **When** Agent 诊断, **Then** Agent 主动追问（浏览器、网络、具体错误信息）

---

### User Story 3 - VPN/连接问题排查 (Priority: P2)

远程办公员工 VPN 每 10–15 分钟断开，无法访问内部工具。

**Why this priority**: 覆盖硬件/连接类问题，展示 Agent 引导分步排查的能力。

**Independent Test**: 输入 VPN 频繁断开场景，Agent 检索 KB runbook、查询用户设备信息、检查 VPN 服务状态，给出排查流程。

**Acceptance Scenarios**:

1. **Given** VPN 服务状态正常, **When** Agent 诊断, **Then** Agent 按 KB runbook 引导检查网络、客户端版本、证书
2. **Given** VPN 网关有 maintenance 记录, **When** Agent 查询状态, **Then** Agent 告知维护窗口并建议等待或备用接入方式
3. **Given** 排查后仍无法解决, **When** Agent 判定超出能力, **Then** 升级并附完整诊断摘要

---

### User Story 4 - 权限/访问申请 (Priority: P2)

新员工加入 Data Engineering 团队，需要 Snowflake 生产库和 Grafana 仪表盘访问权限。

**Why this priority**: 演示策略规则引擎——区分 Agent 可批准 vs. 需人工审批的权限请求。

**Independent Test**: 输入权限申请，Agent 查询用户目录确认角色、检索策略规则，告知哪些可自助开通、哪些需经理/安全团队审批。

**Acceptance Scenarios**:

1. **Given** 策略允许 Grafana read-only 自助开通, **When** 员工申请 Grafana 访问, **Then** Agent 说明可立即开通的步骤或模拟开通确认
2. **Given** Snowflake 生产库需经理审批, **When** 员工申请, **Then** Agent 明确告知需审批、列出所需信息，并生成升级摘要
3. **Given** 员工角色与申请权限不匹配, **When** Agent 查询策略, **Then** Agent 拒绝并解释原因，建议正确流程

---

### User Story 5 - 复杂多系统问题升级 (Priority: P3)

IT 维护窗口后团队数据管道失败，Jenkins 超时，Tableau 报表 stale。

**Why this priority**: 验证 Agent 对复杂跨系统问题的边界判断与高质量升级能力。

**Independent Test**: 输入多系统故障描述，Agent 应查询各系统状态、检索历史案例，判定超出自助范围并生成结构化升级包。

**Acceptance Scenarios**:

1. **Given** 问题涉及 Jenkins + Tableau + 数据管道, **When** Agent 诊断, **Then** Agent 汇总各系统状态与已知变更，判定需升级至 Data Platform 团队
2. **Given** Agent 无法直接修复, **When** 升级, **Then** 升级摘要包含：问题描述、时间线、已查系统状态、已尝试步骤、建议优先级与负责团队

---

### Edge Cases

- 员工描述极其模糊（"电脑坏了"）→ Agent 必须追问具体症状，不得猜测
- KB 无匹配文章 → Agent 声明知识库未覆盖，尝试历史案例或升级
- 系统状态与用户描述冲突 → Agent 透明说明冲突，请用户确认
- 工具调用失败（API 超时）→ Agent 告知暂时无法查询，建议稍后重试或升级
- 员工请求超出 Agent 权限的操作（如直接修改生产权限）→ Agent 拒绝并引用策略规则
- 员工同时提出多个无关问题 → Agent 识别并建议逐一处理

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 提供多轮对话界面（CLI 或 Web 聊天），员工以自然语言描述 IT 问题
- **FR-002**: Agent MUST 在回复前通过工具查询至少一个后端数据源（KB / 状态 / 用户目录 / 历史 / 策略）
- **FR-003**: Agent MUST 维护会话状态，跟踪已调查项、待确认项、当前诊断假设
- **FR-004**: Agent MUST 在信息不足时主动提出澄清问题，而非一次性给出结论
- **FR-005**: Agent MUST 依据策略规则判定是否可直接解决或必须升级人工
- **FR-006**: 升级时 Agent MUST 生成结构化摘要（问题、时间线、工具结果、建议优先级、推荐负责团队）
- **FR-007**: Agent MUST NOT 编造 KB 中不存在或未通过工具验证的解决方案
- **FR-008**: Agent MUST NOT 执行策略禁止的操作（如未经审批开通生产数据库写权限）
- **FR-009**: 系统 MUST 提供 Mock 数据源：知识库（Markdown）、系统状态（JSON）、用户目录（JSON）、历史案例（JSON）、策略规则（JSON）
- **FR-010**: 系统 MUST 包含评估套件，覆盖至少 5 个对话场景及预期结果（resolved / escalated / needs-info）
- **FR-011**: 系统 MUST 记录结构化日志：用户输入、工具调用、Agent 推理步骤、最终决策
- **FR-012**: Agent MUST 在置信度不足时明确告知员工，并说明下一步建议

### Key Entities

- **Employee（员工）**: 姓名、邮箱、部门、角色、办公地点、分配设备、当前权限
- **ConversationSession（会话）**: 会话 ID、消息历史、诊断状态、已调用工具及结果、升级摘要
- **KnowledgeArticle（知识库文章）**: 标题、分类、内容、适用场景标签
- **ServiceStatus（服务状态）**: 服务名、健康状态、影响范围、已知问题描述、ETA
- **ResolutionRecord（历史案例）**: 问题摘要、解决方案、涉及系统、解决时间
- **PolicyRule（策略规则）**: 操作类型、允许条件、审批要求、Agent 权限边界
- **EscalationPackage（升级包）**: 问题摘要、上下文、工具查询结果、建议优先级、目标团队

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: P1 场景（密码问题、软件性能）在 5 轮对话内达到 resolved 或 escalated 结论
- **SC-002**: 评估套件中至少 80% 的场景产生与预期一致的决策（resolved / escalated / needs-info）
- **SC-003**: 100% 的升级场景包含完整上下文摘要，人工接手无需员工重复描述
- **SC-004**: Agent 在 KB 无匹配时零幻觉——不引用不存在的文章或步骤
- **SC-005**: 本地环境从 clone 到首次对话可在 10 分钟内完成（含依赖安装）
- **SC-006**: 演示时面试官输入的新问题，Agent 能完成至少一轮有意义的工具调用与追问

## Assumptions

- 员工身份通过模拟用户目录识别（无需真实 SSO）
- LLM API（Google Gemini 或 Anthropic）可用，密钥由环境变量提供
- v1 不集成 Slack/Teams/ServiceNow，但架构预留扩展点
- Mock 数据为英文（匹配题目示例），Agent 可中英文对话
- 「模拟开通权限」仅返回确认消息，不连接真实 IAM 系统
- 评估以自动化对话脚本 + 人工抽检结合
