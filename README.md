# IT Helpdesk Agent

面向企业员工的对话式 IT 支持 Agent：通过 LangGraph 编排多轮诊断，调用 Mock 工具（KB、系统状态、用户目录、历史案例、策略规则），在可自助解决时给出分步指引，超出能力时生成结构化升级包交给人工处理。

## 问题与目标

传统 IT 工单流程耗时长，大量重复问题（密码重置、VPN、权限申请）已有成熟 runbook，但仍需人工逐单处理。本项目演示 **Agentic AI** 如何：

- 用自然语言理解员工问题并主动追问
- 基于工具结果（非幻觉）给出诊断与步骤
- 明确区分 **自助解决 / 澄清 / 升级** 边界
- 升级时输出完整 **Escalation Package** 供人工接手

## 技术栈

| 组件 | 选型 |
|------|------|
| 语言 | Python 3.12 |
| Agent 编排 | LangGraph + LangChain |
| LLM | Google Gemini / Anthropic（可切换） |
| CLI | Typer + Rich |
| API（可选） | FastAPI |
| 数据 | 本地 JSON + Markdown Mock |
| 测试 | pytest + YAML 评估场景 |

## 架构

```text
员工输入 (CLI / API)
       │
       ▼
┌──────────────┐
│ intake       │  分类 + 模糊检测
└──────┬───────┘
       │
   ┌───┴───┬─────────┬─────────┬─────────┬─────────┐
   ▼       ▼         ▼         ▼         ▼         ▼
password software   vpn     access   complex  investigate
 (US1)    (US2)   (US3)    (US4)    (US5)    (LLM+tools)
   │       │         │         │         │
   └───┬───┴────┬────┴────┬────┴────┬────┘
       ▼        ▼         ▼         ▼
   resolve   clarify   escalate
```

**确定性路径**（Okta、Salesforce、VPN、权限、多系统管道）不依赖 LLM，评估可离线运行；通用问题走 LLM + tool calling。

## 决策边界

| 决策 | 条件 |
|------|------|
| **resolve** | KB/策略允许自助；已知 outage 告知 ETA；可模拟开通的权限 |
| **clarify** | 描述模糊、缺少范围/错误信息 |
| **escalate** | 账户锁定、需审批权限、多系统故障、策略禁止、排查无效 |

Agent **不得**编造 KB 内容或直接修改生产权限。

## Mock 数据

```text
src/data/
├── kb/           # Markdown 知识库（Okta、VPN、Salesforce、权限等）
├── status/       # 服务健康状态（Okta、Salesforce、VPN、Jenkins、Tableau）
├── users/        # 员工 persona（Sales、Data Eng、锁定账户等）
├── history/      # 历史解决案例
└── policies/     # 策略规则（自助 vs 审批 vs 拒绝）
```

## 快速开始

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env   # 可选：配置 GEMINI_API_KEY 用于 LLM 路径

# 单次问答（确定性场景无需 API Key）
python -m src.cli.main ask "I can't log into Okta, password reset didn't work" --employee emp-001

# 交互式对话
python -m src.cli.main chat --employee emp-001

# 直接调用工具
python -m src.cli.main tool kb-search --query "okta password reset"
python -m src.cli.main tool status --service jenkins
python -m src.cli.main tool user --id emp-002
python -m src.cli.main tool policy --action grant_snowflake_prod --employee emp-002
```

## 评估

```bash
# YAML 场景评估（17 个场景，含 5 US + 边缘 case）
python -m src.cli.main eval
python -m src.cli.main eval --scenario okta --verbose

# 或通过 pytest
pytest tests/eval/ -v
pytest tests/integration/ -v
pytest tests/unit/ -v
```

评估断言：`expected_decision`、`expected_tools`、`must_contain` / `must_not_contain`（避免 exact text 导致 flaky）。

## 可选 API

```bash
uv pip install -e ".[api]"
uvicorn src.api.server:app --reload --port 8000

curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"I cant log into Okta","employee_id":"emp-001"}'
```

## 项目结构

```text
src/agent/          LangGraph 状态机、分类 handlers、升级包
src/tools/          5 个 Mock 工具 + registry
src/cli/            Typer CLI（chat / ask / tool / eval）
src/api/            可选 FastAPI
tests/eval/         YAML 评估 runner + 场景
specs/001-it-helpdesk-agent/   设计文档
```

## 权衡与局限

- **Mock 数据** 非真实 ITSM/Okta/Snowflake 集成，演示编排与边界逻辑
- **确定性 handler** 覆盖 5 个用户故事；其余走 LLM，需 API Key
- **无持久化会话**（CLI 内存 / API 内存），重启丢失
- **评估优先 decision + tools**，非 exact 回复文本

## 后续改进

- 接入真实 ServiceNow / Okta / Splunk API
- 会话持久化（Redis / DB）
- Streamlit Web UI
- LLM-as-judge 评估层
- 多问题拆分与排队处理

## 文档

- [Spec](specs/001-it-helpdesk-agent/spec.md)
- [Plan](specs/001-it-helpdesk-agent/plan.md)
- [Quickstart](specs/001-it-helpdesk-agent/quickstart.md)
- [Tool Contracts](specs/001-it-helpdesk-agent/contracts/agent-tools.md)

## License

Internal take-home / demo project.
