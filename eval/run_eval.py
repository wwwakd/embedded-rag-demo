#!/usr/bin/env python3
"""Section-level retrieval evaluation.

Metrics:
  section@1   the first returned section is a correct one
  section@3   a correct section appears in the top 3
  hit@5       a correct section appears in the top 5

Run:
  python eval/run_eval.py                 # with the Chinese bridge (zh summary)
  python eval/run_eval.py --ablate zh     # without it - shows the cross-lingual gap
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from retrieval.chunking import build_chunks          # noqa: E402
from retrieval.hybrid import HybridIndex             # noqa: E402
from retrieval.rerank_gate import needs_rerank, term_coverage  # noqa: E402


def load_questions(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run(use_zh: bool, show: bool, expand: bool = True) -> dict:
    manual = (ROOT / "data" / "manual" / "synth28335_sample.md").read_text(encoding="utf-8")
    chunks = build_chunks(manual)
    index = HybridIndex(chunks, alpha=0.6, use_zh=use_zh, expand=expand)
    questions = load_questions(ROOT / "eval" / "questions.jsonl")

    s1 = s3 = hit5 = 0
    rows = []
    for item in questions:
        ranking = index.section_ranking(item["q"], top_k=5)
        sections = [sid for sid, _ in ranking]
        expect = set(item["expect"])

        # conditional rerank: navigation questions keep the entry order,
        # factual questions are re-ordered by term coverage
        if needs_rerank(item["q"]):
            rescored = []
            for sid, base in ranking:
                text = " ".join(c.text + " " + c.zh for c in chunks if c.section_id == sid)
                rescored.append((sid, base * (0.7 + 0.3 * term_coverage(item["q"], text))))
            sections = [sid for sid, _ in sorted(rescored, key=lambda kv: kv[1], reverse=True)]

        ok1 = sections[0] in expect if sections else False
        ok3 = any(s in expect for s in sections[:3])
        ok5 = any(s in expect for s in sections[:5])
        s1 += ok1
        s3 += ok3
        hit5 += ok5
        rows.append((item["q"], item["type"], sections[:3], ok1, ok3))

    total = len(questions)
    if show:
        print(f"{'question':44s} {'type':10s} {'top3':22s} @1  @3")
        for q, t, top3, ok1, ok3 in rows:
            print(f"{q[:42]:44s} {t:10s} {','.join(top3)[:20]:22s} {'Y' if ok1 else '-':3s} {'Y' if ok3 else '-'}")
        print()

    return {
        "n": total,
        "section@1": round(100 * s1 / total, 1),
        "section@3": round(100 * s3 / total, 1),
        "hit@5": round(100 * hit5 / total, 1),
        "chunks": len(chunks),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ablate", choices=["none", "zh", "crosslingual"], default="none",
                    help="zh = drop the Chinese summary bridge; crosslingual = drop summary + alias expansion")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    with_zh = run(True, args.show)
    print("with zh bridge :", with_zh)

    if args.ablate == "zh":
        without = run(False, False)
        print("without bridge :", without)
        print(f"delta section@1: {with_zh['section@1'] - without['section@1']:+.1f} pt")
    elif args.ablate == "crosslingual":
        without = run(False, False, expand=False)
        print("no cross-lingual layer:", without)
        print(f"delta section@1: {with_zh['section@1'] - without['section@1']:+.1f} pt")
        print(f"delta hit@5    : {with_zh['hit@5'] - without['hit@5']:+.1f} pt")


if __name__ == "__main__":
    main()
