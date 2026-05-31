"""Unit tests for KB formatting helpers."""

import pytest

from src.tools.kb_format import kb_article_text, kb_runbook_for_reply, make_snippet


@pytest.mark.unit
def test_make_snippet_truncates_at_line_boundary():
    content = "## Steps\n1. First step here\n2. Second step here\n3. Third step"
    snippet = make_snippet(content, max_len=30)
    assert snippet.endswith("…")
    assert "Second step" not in snippet


@pytest.mark.unit
def test_kb_runbook_for_reply_omits_escalate_section():
    content = "## Steps\n1. Do thing\n\n## Escalate if\n- Still broken"
    assert "Escalate if" not in kb_runbook_for_reply(content)
    assert "Do thing" in kb_runbook_for_reply(content)


@pytest.mark.unit
def test_kb_article_text_prefers_full_content():
    article = {"content": "Full runbook body", "snippet": "Short…"}
    assert kb_article_text(article) == "Full runbook body"


@pytest.mark.unit
def test_vpn_reply_includes_complete_steps():
    from src.agent.vpn_handlers import apply_vpn_rules, prefetch_vpn_tools

    msg = "My VPN keeps disconnecting every 10-15 minutes."
    records = prefetch_vpn_tools("emp-001", msg)
    decision, reply, _, _ = apply_vpn_rules(records, msg)
    assert decision == "resolve"
    assert "Update GlobalProtect to latest version (6.2+)" in reply
    assert "…" not in reply.split("## Steps")[1][:120]
