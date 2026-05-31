# Bug 记录：多轮对话中 clarify 决策「粘住」

**日期**：2026-05-31  
**影响范围**：`chat` 多轮交互  
**状态**：已修复

---

## 现象

在 `python -m src.cli.main chat` 中，用户先问了一个**模糊问题**（如 `"My computer is broken. Help me."`）后，后续输入**具体、完整**的 IT 问题（VPN 断连、Snowflake 权限等），Agent 仍反复回复：

```text
I'd like to help, but I need a bit more detail.

- What exactly happens when you try to use it?
- When did the issue start, and is it affecting only you or your whole team?
```

日志中 `decision=clarify`，且 `tools=0`（未调用任何诊断工具）。

## 对比：正常 vs 异常

| 场景 | 预期 | 实际（修复前） |
|------|------|----------------|
| 新开 session，直接问 VPN | `resolve`，调用 kb/status/user | ✅ 正常 |
| 先问模糊问题，再问 VPN | 第二轮应重新诊断 | ❌ 仍 `clarify` |
| `ask` 单次命令 | 每轮新 session | ✅ 正常 |

## 根因

LangGraph 会话状态在多轮之间**持久保留** `decision` 字段。

1. 模糊输入触发 `intake_node` 设置 `decision=clarify` 和 `pending_questions`
2. 下一轮具体输入进入 `intake_node` 时，**未清除**上一轮的 `decision`
3. `route_after_intake` 优先检查 `decision == clarify`，直接路由到 `clarify_node`，跳过分类与工具调用

相关代码路径：

```text
intake_node          → 写入 decision=clarify（仅模糊输入时）
route_after_intake   → if decision == clarify → clarify_node → END
```

## 修复

在 `src/agent/nodes.py` 的 `intake_node` 中，**每轮开始时**重置路由相关字段：

```python
updates = {
    ...
    "decision": None,
    "pending_questions": [],
}
# 仅当当前消息模糊或信息不足时，再设为 clarify
```

原则：**每轮路由决策只由当前用户消息决定**，不受上一轮 `clarify` 污染。

## 验证

新增单元测试 `test_clarify_decision_does_not_stick_on_next_turn`（`tests/unit/test_agent_foundation.py`）：

1. 第一轮：模糊输入 → `decision=clarify`
2. 第二轮：VPN 具体问题 → `decision=resolve`

手动验证：

```bash
python -m src.cli.main chat --employee emp-001
# 1. My computer is broken. Help me.     → clarify（预期）
# 2. My VPN keeps disconnecting every...   → resolve + 工具调用（修复后）
```

## 使用建议

- 修复前已开启的 `chat` session 可能残留旧状态，**退出后重新进入**再测
- 演示时若需稳定结果，可用 `ask`（每轮独立 session）或重新 `chat`
- 模糊短句（如 `"can't turn on"`）仍会触发 `clarify`，这是产品设计，不是 bug

---

## 相关问题：KB 回复内容截断

**现象**：VPN 等场景回复中 runbook 在 `1 Update GlobalProtect to ...` 处被截断。

**根因**：`kb_search` 将 `snippet` 硬截断为 240 字符；handler 嵌入 snippet 而非完整正文，且 VPN handler 还重复硬编码了步骤列表。

**修复**（2026-05-31）：
- `kb_search` 返回完整 `content` 字段；`snippet` 仅用于搜索预览，按行/词边界截断
- Agent 回复使用 `kb_article_text(..., for_reply=True)` 读取完整 runbook
- 展示时省略 KB 文末 `## Escalate if` 节，避免与 `resolve` 决策语义冲突

详见 `src/tools/kb_format.py`。

## 关联文件

| 文件 | 变更 |
|------|------|
| `src/agent/nodes.py` | `intake_node` 每轮重置 `decision` / `pending_questions` |
| `tests/unit/test_agent_foundation.py` | 新增多轮回归测试 |
