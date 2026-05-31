"""Knowledge base search tool."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.models.schemas import KBCategory, ToolResponse
from src.paths import DATA_DIR
from src.tools.base import fail, ok
from src.tools.kb_format import make_snippet

KB_DIR = DATA_DIR / "kb"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass
class ParsedArticle:
    id: str
    title: str
    category: str
    tags: list[str]
    content: str


def _parse_frontmatter(text: str) -> dict[str, str | list[str]]:
    meta: dict[str, str | list[str]] = {}
    match = FRONTMATTER_RE.match(text)
    if not match:
        return meta
    block = match.group(1)
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip() for v in value[1:-1].split(",")]
            meta[key] = items
        else:
            meta[key] = value.strip('"')
    return meta


def _load_articles() -> list[ParsedArticle]:
    articles: list[ParsedArticle] = []
    for path in sorted(KB_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta = _parse_frontmatter(text)
        body_match = FRONTMATTER_RE.match(text)
        body = body_match.group(2) if body_match else text
        articles.append(
            ParsedArticle(
                id=str(meta.get("id", path.stem)),
                title=str(meta.get("title", path.stem)),
                category=str(meta.get("category", "software")),
                tags=list(meta.get("tags", [])),
                content=body.strip(),
            )
        )
    return articles


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-z0-9]+", text.lower())}


def _score(query_tokens: set[str], article: ParsedArticle) -> float:
    corpus = " ".join([article.title, article.category, " ".join(article.tags), article.content])
    doc_tokens = _tokenize(corpus)
    if not query_tokens or not doc_tokens:
        return 0.0
    overlap = len(query_tokens & doc_tokens)
    return overlap / len(query_tokens)


def kb_search(query: str, category: str | None = None, limit: int = 3) -> ToolResponse:
    if not query.strip():
        return fail("kb_search", "query is required")

    query_tokens = _tokenize(query)
    scored: list[tuple[float, ParsedArticle]] = []

    for article in _load_articles():
        if category and article.category != category:
            continue
        score = _score(query_tokens, article)
        if score > 0:
            scored.append((score, article))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]

    articles = [
        {
            "id": a.id,
            "title": a.title,
            "category": a.category,
            "tags": a.tags,
            "content": a.content,
            "snippet": make_snippet(a.content),
            "relevance_score": round(score, 2),
        }
        for score, a in top
    ]

    return ok("kb_search", {"articles": articles, "total_found": len(articles)})


def validate_category(category: str) -> bool:
    try:
        KBCategory(category)
        return True
    except ValueError:
        return False
