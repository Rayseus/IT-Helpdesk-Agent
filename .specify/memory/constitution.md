# IT Helpdesk Agent Constitution

## Core Principles

### I. Employee-First Experience

系统面向**遇到 IT 问题的员工**，而非 IT 运维人员。交互必须像与资深 IT 专员对话，而非填工单表单。所有设计决策以员工能否在 2 分钟内获得可执行帮助为首要标准。

### II. Agentic, Not One-Shot

禁止单次 LLM 调用即给出最终答案的模式。Agent 必须通过多轮对话诊断、多源信息检索、假设形成与验证来驱动问题解决。每个会话必须维护显式状态（已调查项、待确认项、当前假设）。

### III. Tool-Grounded Reasoning

Agent 的每个结论必须可追溯到工具调用结果（知识库、系统状态、用户目录、历史案例、策略规则）。禁止在无数据支撑时编造解决方案。工具失败时必须透明告知并尝试替代路径。

### IV. Resolution vs. Escalation Boundary

Agent 必须明确区分「可直接解决」与「必须升级人工」的边界，依据策略规则引擎判定。升级时必须生成完整上下文摘要（问题描述、已尝试步骤、工具查询结果、建议优先级），员工无需重复叙述。

### V. Evaluation-Driven Development

每个核心用户场景必须有可执行的对话测试用例及预期结果（resolved / escalated / needs-info）。交付前必须运行评估套件并记录通过率与失败案例。

### VI. Simplicity & Local Runnability

优先选择可本地运行的最小可行架构。Mock 数据足够丰富以演示多源推理即可，不追求生产级规模。外部依赖必须文档化且可一键安装。

## Technical Constraints

- 语言：Python 3.12+
- 必须可在本地运行，不依赖专有云服务（LLM API 除外）
- Mock 数据源至少覆盖 3 类：知识库、系统状态、用户目录（另含策略规则与历史案例）
- 交互界面：CLI 或轻量 Web 聊天（二选一，优先 CLI 以降低复杂度）
- 日志与可观测性：结构化日志记录工具调用、推理步骤、升级决策

## Quality Gates

- 所有 P1 用户场景有对应集成测试
- Agent 不得在策略禁止的操作上越权（如直接重置生产数据库权限）
- 模糊/不完整输入时 Agent 必须追问而非猜测
- README 必须包含架构说明、运行方式、评估方法与已知限制

## Governance

本 Constitution 优先于所有实现细节。修订需更新 `.specify/memory/constitution.md` 版本号并同步 plan/spec。所有 speckit 产物（spec → plan → tasks → implement）必须依次通过 Constitution Check。

**Version**: 1.0.0 | **Ratified**: 2026-05-28 | **Last Amended**: 2026-05-28
