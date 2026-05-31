# Research: IT Helpdesk Agent

**Date**: 2026-05-28

## R1: Agent 编排框架

**Decision**: LangGraph

**Rationale**:
- 原生支持 cyclic graph（诊断 ↔ 工具调用循环）
- 显式 TypedDict state，满足 Constitution「会话状态跟踪」要求
- 与 LangChain tool calling 集成成熟
- 社区示例丰富，适合 take-home 时间线

**Alternatives considered**:
| 方案 | 放弃原因 |
|------|----------|
| 纯 LangChain AgentExecutor | 状态不透明，多轮控制弱 |
| AutoGen / CrewAI | 多 Agent 协作过度设计 |
| 手写 while-loop + Gemini tools | 可行但缺少结构化状态管理 |

## R2: LLM 提供商

**Decision**: Google Gemini 2.0 Flash 默认，Anthropic claude-sonnet-4 可选（env 切换）

**Rationale**:
- Gemini 2.0 Flash 工具调用 JSON schema 稳定
- 两者均支持 function calling
- 通过 `LLM_PROVIDER` env 抽象，避免 vendor lock-in

**Alternatives considered**:
| 方案 | 放弃原因 |
|------|----------|
| 本地 Ollama | 工具调用质量不稳定，demo 风险高 |
| 仅 Claude | 无必要限制，双 provider 更灵活 |

## R3: 知识库检索

**Decision**: 关键词匹配 + 简单 BM25/TF-IDF（scikit-learn 或 hand-rolled）

**Rationale**:
- Mock KB 预计 10–20 篇文章，向量 DB 过度
- 可预测、可测试、无额外 infra
- 评估时可断言「调用了 kb_search 且返回了 okta-password-reset」

**Alternatives considered**:
| 方案 | 放弃原因 |
|------|----------|
| ChromaDB + embeddings | 增加依赖与启动时间 |
| 全文 LLM 扫描 | 成本高、不可预测 |

## R4: 交互界面

**Decision**: Typer CLI 为主，FastAPI endpoint 预留

**Rationale**:
- 题目明确「不追求 polished UI」
- CLI 面试 demo 最直接（面试官打字即对话）
- Typer + Rich 提供可读输出
- FastAPI `/chat` endpoint 供后续 Streamlit 接入

**Alternatives considered**:
| 方案 | 放弃原因 |
|------|----------|
| Streamlit 优先 | 开发时间更长，非核心考察点 |
| 纯 Jupyter | 不适合 live demo 对话 |

## R5: Mock 数据格式

**Decision**:
- KB: Markdown 文件 + frontmatter（title, tags, category）
- 其余: JSON 文件，按实体类型分目录

**Rationale**:
- Markdown 贴近真实 IT runbook
- JSON 易于 pytest fixture 加载
- 文件系统即「数据库」，零配置

## R6: 评估方法

**Decision**: YAML 场景定义 + pytest parametrized tests

**Rationale**:
- 场景即文档，面试官可直观看到覆盖范围
- `expected_decision` + `expected_tools` 断言稳定
- 避免 LLM-as-judge 的 flaky

**Alternatives considered**:
| 方案 | 放弃原因 |
|------|----------|
| LLM 评分 | 不稳定、不可复现 |
| 纯人工 | 无法 CI、回归困难 |

## R7: 日志与可观测性

**Decision**: Python structlog → stdout + 可选 JSON 文件

**Rationale**:
- 满足 Constitution observability 要求
- 面试时可展示 tool call trace
- 不引入 LangSmith 等外部依赖（可选 env 开启）

## R8: 升级包格式

**Decision**: 结构化 Markdown 块 + JSON sidecar

```json
{
  "issue_summary": "...",
  "timeline": "...",
  "tools_invoked": [...],
  "diagnosis": "...",
  "attempted_steps": [...],
  "recommended_priority": "P1|P2|P3",
  "target_team": "IT Helpdesk|Data Platform|Security",
  "employee_context": {...}
}
```

**Rationale**:
- 人类可读（Markdown）+ 机器可解析（JSON）
- 模拟 ServiceNow ticket payload

## Open Questions (Resolved)

| 问题 | 决议 |
|------|------|
| 是否需要 Web UI | v1 可选，CLI 足够 |
| 是否需要向量 DB | 否 |
| 是否需要真实 IAM 集成 | 否，模拟确认即可 |
| 评估 pass 阈值 | 80% 场景 decision 一致 |
