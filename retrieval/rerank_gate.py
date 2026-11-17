"""Conditional reranking.

Reranking is not a free win. For navigation questions ("which section defines X")
a reranker tends to promote paragraphs that look like answers and push the section
entry down. So the gate decides per query whether reranking should run at all.
"""

from __future__ import annotations

NAVIGATION_HINTS = (
    "哪一节", "哪个章节", "在哪一", "在哪节", "哪章",
    "which section", "where is", "where can i find the section",
)

FACT_HINTS = (
    "默认值", "复位值", "多少位", "什么值", "怎么配", "如何配置",
    "reset value", "bit field", "how to configure",
)


def is_navigation(query: str) -> bool:
    q = query.lower()
    return any(h in q for h in NAVIGATION_HINTS)


def needs_rerank(query: str) -> bool:
    """Navigation questions skip reranking; factual lookups keep it."""
    if is_navigation(query):
        return False
    return True


def term_coverage(query: str, text: str) -> float:
    """Cheap rerank proxy: how many query tokens/char-bigrams appear in the text."""
    text = text.lower()
    q = query.lower()
    keys = [w for w in q.replace("，", " ").split() if len(w) > 1]
    if not keys:
        keys = [q[i:i + 2] for i in range(len(q) - 1)]
    if not keys:
        return 0.0
    hit = sum(1 for k in keys if k in text)
    return hit / len(keys)
