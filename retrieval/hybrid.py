"""Hybrid retrieval: character n-gram TF-IDF + BM25, fused by weighted score.

Why character n-grams instead of word tokens: the queries are Chinese, the manual is
English, and domain abbreviations (GPAMUX1, ACQPS) do not survive word tokenization.
Character n-grams keep the surface form intact and are robust to missing segmentation.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .bm25 import BM25
from .chunking import Chunk
from .normalize import EntityNormalizer

CJK = re.compile(r"[\u4e00-\u9fff]")


def char_ngrams(text: str, lo: int = 2, hi: int = 5) -> Counter:
    s = re.sub(r"\s+", " ", text.lower())
    grams: Counter = Counter()
    for n in range(lo, hi + 1):
        for i in range(len(s) - n + 1):
            gram = s[i:i + n]
            if CJK.search(gram) or gram.isalnum():
                grams[gram] += 1
    return grams


class HybridIndex:
    def __init__(self, chunks: list[Chunk], alpha: float = 0.6, use_zh: bool = True, expand: bool = True):
        self.chunks = chunks
        self.alpha = alpha
        self.expand = expand
        self.normalizer = EntityNormalizer()
        docs = [self._doc_text(c, use_zh) for c in chunks]
        self.docs = docs
        self.bm25 = BM25(docs)

        self.grams = [char_ngrams(d) for d in docs]
        df: Counter = Counter()
        for g in self.grams:
            df.update(set(g))
        n = len(docs)
        self.idf = {k: math.log((n + 1) / (v + 1)) + 1 for k, v in df.items()}
        self.vector = [self._tfidf_vector(g) for g in self.grams]

    @staticmethod
    def _doc_text(chunk: Chunk, use_zh: bool) -> str:
        parts = [chunk.section_title, chunk.text]
        if use_zh and chunk.zh:
            parts.append(chunk.zh)
        return "\n".join(parts)

    def _tfidf_vector(self, grams: Counter) -> dict:
        vec = {g: (1 + math.log(c)) * self.idf.get(g, 0.0) for g, c in grams.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {g: v / norm for g, v in vec.items()}

    @staticmethod
    def _cosine(a: dict, b: dict) -> float:
        if len(a) > len(b):
            a, b = b, a
        return sum(v * b.get(g, 0.0) for g, v in a.items())

    def _vector_scores(self, query: str) -> list[float]:
        qvec = self._tfidf_vector(char_ngrams(query))
        return [self._cosine(qvec, v) for v in self.vector]

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        q = self.normalizer.expand(query) if self.expand else self.normalizer.normalize(query)
        vec = self._vector_scores(q)
        lex = self.bm25.scores(q)
        vec_max = max(vec) or 1.0
        lex_max = max(lex) or 1.0
        fused = [
            self.alpha * (vec[i] / vec_max) + (1 - self.alpha) * (lex[i] / lex_max)
            for i in range(len(vec))
        ]
        order = sorted(range(len(fused)), key=lambda i: fused[i], reverse=True)[:top_k]
        return [(self.chunks[i], fused[i]) for i in order]

    def section_ranking(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        best: dict[str, float] = {}
        for chunk, score in self.search(query, top_k=max(top_k * 4, 20)):
            best[chunk.section_id] = max(best.get(chunk.section_id, 0.0), score)
        return sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
