"""Helpers for formatting KB article text in tool output and agent replies."""

from __future__ import annotations

import re


def make_snippet(content: str, max_len: int = 240) -> str:
    """Short preview for search listings; truncate at line or word boundary."""
    text = content.strip()
    if len(text) <= max_len:
        return text

    cut = text[:max_len]
    last_nl = cut.rfind("\n")
    if last_nl > max_len * 0.4:
        cut = cut[:last_nl]
    else:
        last_space = cut.rfind(" ")
        if last_space > max_len * 0.6:
            cut = cut[:last_space]

    return cut.rstrip() + "…"


def kb_runbook_for_reply(content: str) -> str:
    """Self-service runbook body; omit trailing 'Escalate if' guidance section."""
    lines = content.splitlines()
    kept: list[str] = []
    skip = False
    for line in lines:
        if re.match(r"^##\s+Escalate if\b", line, re.IGNORECASE):
            skip = True
            continue
        if skip and line.startswith("## "):
            skip = False
        if not skip:
            kept.append(line)
    return "\n".join(kept).strip()


def kb_article_text(article: dict, *, prefer_full: bool = True, for_reply: bool = False) -> str:
    """Return full article body when available, else the search snippet."""
    if prefer_full:
        content = article.get("content")
        if content:
            text = str(content).strip()
            return kb_runbook_for_reply(text) if for_reply else text
    return str(article.get("snippet") or "").strip()
