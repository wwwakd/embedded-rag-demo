"""Structure-aware chunking for technical manuals.

The core idea: a register field table that is split away from its header becomes
useless ("row has a value but no meaning"). So every chunk carries its section title
and, when available, the Chinese summary of that section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

HEADING = re.compile(r"^(#{2,3})\s+(.+)$")
NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)")


@dataclass
class Chunk:
    chunk_id: str
    section_id: str
    section_title: str
    kind: str          # "text" | "table"
    text: str
    zh: str = ""

    @property
    def indexable_text(self) -> str:
        parts = [self.section_title, self.text]
        if self.zh:
            parts.append(self.zh)
        return "\n".join(parts)


def _split_blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    blocks: list[tuple[str, list[str]]] = []
    buf: list[str] = []
    kind = None
    for line in lines:
        if not line.strip():
            if buf:
                blocks.append((kind or "text", buf))
                buf = []
            kind = None
            continue
        cur = "table" if line.strip().startswith("|") else "text"
        if kind is None:
            kind = cur
        if cur != kind:
            if buf:
                blocks.append((kind, buf))
            buf = []
            kind = cur
        buf.append(line)
    if buf:
        blocks.append((kind or "text", buf))
    return blocks


def _sections(md_text: str):
    sections = []
    cur = {"id": None, "title": None, "lines": []}
    for line in md_text.split("\n"):
        m = HEADING.match(line)
        if m:
            if cur["id"] is not None:
                sections.append(cur)
            title = m.group(2).strip()
            num = NUMBERED.match(title)
            cur = {"id": num.group(1) if num else title, "title": title, "lines": []}
        else:
            cur["lines"].append(line)
    if cur["id"] is not None:
        sections.append(cur)
    return sections


def build_chunks(md_text: str, max_chars: int = 1200) -> list[Chunk]:
    chunks: list[Chunk] = []
    for sec in _sections(md_text):
        raw_zh = [ln[3:].strip() for ln in sec["lines"] if ln.strip().lower().startswith("zh:")]
        zh = " ".join(raw_zh)
        body = [ln for ln in sec["lines"] if not ln.strip().lower().startswith("zh:")]

        n = 0
        for kind, block in _split_blocks(body):
            piece: list[str] = []
            size = 0
            for line in block:
                if piece and size + len(line) > max_chars:
                    chunks.append(Chunk(
                        chunk_id=f"{sec['id']}#{n}",
                        section_id=sec["id"],
                        section_title=sec["title"],
                        kind=kind,
                        text="\n".join(piece),
                        zh=zh,
                    ))
                    n += 1
                    piece, size = [], 0
                piece.append(line)
                size += len(line)
            if piece:
                chunks.append(Chunk(
                    chunk_id=f"{sec['id']}#{n}",
                    section_id=sec["id"],
                    section_title=sec["title"],
                    kind=kind,
                    text="\n".join(piece),
                    zh=zh,
                ))
                n += 1
    return chunks
