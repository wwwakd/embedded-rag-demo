"""Minimal BM25 over word tokens (English-heavy manuals)."""

from __future__ import annotations

import math
import re
from collections import Counter

TOKEN = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tokens = [tokenize(d) for d in docs]
        self.n = len(docs)
        self.doc_len = [len(t) for t in self.tokens]
        self.avg = sum(self.doc_len) / max(self.n, 1)
        df: Counter = Counter()
        for toks in self.tokens:
            df.update(set(toks))
        self.idf = {w: math.log(1 + (self.n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self.freq = [Counter(t) for t in self.tokens]

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        out = []
        for i in range(self.n):
            s = 0.0
            dl = self.doc_len[i] or 1
            for w in q:
                if w not in self.idf:
                    continue
                f = self.freq[i].get(w, 0)
                if not f:
                    continue
                s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avg))
            out.append(s)
        return out
