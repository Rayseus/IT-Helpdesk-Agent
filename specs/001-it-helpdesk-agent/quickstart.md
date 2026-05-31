# Quickstart: IT Helpdesk Agent

**Date**: 2026-05-28

## Prerequisites

- Python 3.12+（`brew install python@3.12` 或 `uv python install 3.12`）
- [uv](https://docs.astral.sh/uv/) 包管理器
- Google Gemini 或 Anthropic API Key

## Setup

```bash
# 克隆并进入项目
cd yaoming-test

# 创建虚拟环境并安装依赖
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"

# 配置 API Key
cp .env.example .env
# 编辑 .env:
#   LLM_PROVIDER=gemini          # 或 anthropic
#   GEMINI_API_KEY=your-key-here
#   ANTHROPIC_API_KEY=sk-ant-...   # 若使用 anthropic
```

## Run Interactive Chat

```bash
# 以默认员工身份启动
python -m src.cli.main chat

# 指定员工 persona
python -m src.cli.main chat --employee emp-001

# 单次问题（非交互）
python -m src.cli.main ask "I can't log into Okta"
```

## Run Evaluation

```bash
# 运行全部 YAML 评估场景
python -m src.cli.main eval
python -m src.cli.main eval --scenario okta --verbose

# 或通过 pytest
pytest tests/eval/ -v
```

## Verify Tools Independently

```bash
python -m src.cli.main tool kb-search --query "okta password reset"
python -m src.cli.main tool status --service okta
python -m src.cli.main tool user --id emp-001
python -m src.cli.main tool history --query "salesforce slow"
python -m src.cli.main tool policy --action grant_snowflake_prod --employee emp-002
```

## Demo Flow (Interview)

1. `python -m src.cli.main chat --employee emp-001`
2. 输入密码问题 → 观察 tool calls 与分步指引
3. 输入 Salesforce 慢 → 观察 outage 关联
4. 输入 Snowflake 权限 → 观察策略拒绝/升级
5. 输入模糊问题 "my computer is broken" → 观察追问
6. 展示 `pytest tests/eval/ -v` 评估结果

## Troubleshooting

| 问题 | 解决 |
|------|------|
| `GEMINI_API_KEY not set` | 检查 `.env` 文件 |
| Import 错误 | 确认 `uv pip install -e ".[dev]"` |
| Agent 响应慢 | 正常，含 LLM + 多工具调用 |
| 评估失败 | 检查 API key 与网络 |

## Project Layout

```
src/agent/     → LangGraph 状态机
src/tools/     → 5 个 Mock 工具
src/data/      → Mock JSON/Markdown
tests/eval/    → 对话场景评估
specs/         → speckit 设计文档
```
