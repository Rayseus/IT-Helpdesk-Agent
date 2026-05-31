"""Resolution history search tool."""

from __future__ import annotations

import re

from src.models.schemas import ResolutionRecord
from src.paths import DATA_DIR
from src.tools.base import fail, load_json, ok

HISTORY_DIR = DATA_DIR / "history"


def _load_all_records() -> list[ResolutionRecord]:
    records: list[ResolutionRecord] = []
    seen: set[str] = set()

    for path in sorted(HISTORY_DIR.glob("*.json")):
        data = load_json(path)
        items = data.get("records", [data]) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = [items]
        for item in items:
            record = ResolutionRecord.model_validate(item)
            if record.id in seen:
                continue
            seen.add(record.id)
            records.append(record)
    return records


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-z0-9]+", text.lower())}


def _score(query_tokens: set[str], record: ResolutionRecord) -> float:
    corpus = " ".join(
        [
            record.problem_summary,
            record.resolution,
            record.category,
            " ".join(record.symptoms),
            " ".join(record.systems_involved),
        ]
    )
    doc_tokens = _tokenize(corpus)
    if not query_tokens or not doc_tokens:
        return 0.0
    return len(query_tokens & doc_tokens) / len(query_tokens)


def history_search(
    query: str,
    systems: list[str] | None = None,
    limit: int = 5,
) -> ToolResponse:
    if not query.strip():
        return fail("history_search", "query is required")

    try:
        records = _load_all_records()
    except FileNotFoundError:
        return fail("history_search", "history data unavailable")

    if not records:
        return fail("history_search", "history data unavailable")
    query_tokens = _tokenize(query)
    scored: list[tuple[float, ResolutionRecord]] = []

    systems_lower = [s.lower() for s in (systems or [])]

    for record in records:
        if systems_lower:
            involved = [s.lower() for s in record.systems_involved]
            if not any(s in involved for s in systems_lower):
                continue
        score = _score(query_tokens, record)
        if score > 0:
            scored.append((score, record))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]

    return ok(
        "history_search",
        {
            "records": [r.model_dump(mode="json") for _, r in top],
            "total_found": len(top),
        },
    )
