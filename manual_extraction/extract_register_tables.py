#!/usr/bin/env python3
"""Extract register-related tables from a TI-style technical reference manual PDF.

Usage:
    python manual_extraction/extract_register_tables.py --pdf path/to/manual.pdf
    python manual_extraction/extract_register_tables.py --pdf manual.pdf --max-pages 200

Outputs:
  - out/register_tables_raw/<table-id>.md
  - out/register_tables_csv/<table-id>.csv   (when PyMuPDF detects table cells)
  - out/tms28335_register_tables_manifest.csv

The extractor uses table-title anchors from page text so every register table gets
at least a raw text block grouped by table ID. When `page.find_tables()` can detect
cell geometry, a CSV version is emitted as well.
"""
from __future__ import annotations

import csv
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input"
OUT_DIR = ROOT / "out"
RAW_DIR = OUT_DIR / "raw"
CSV_DIR = OUT_DIR / "csv"
MANIFEST_CSV = OUT_DIR / "manifest.csv"

TABLE_TITLE_RE = re.compile(r"^Table\s+(\d+-\d+)\.\s+(.+?)(?:\s+\(continued\))?$")
REGISTER_TITLE_RE = re.compile(r"\bRegisters?\b")

SKIP_LINES = {
    "www.ti.com",
    "SPRUI07–March 2020",
    "Submit Documentation Feedback",
    "Copyright © 2020, Texas Instruments Incorporated",
    "System Control and Interrupts",
}

TEXT_BLOCK = 0
BOUND_MARGIN = 4.0


@dataclass(frozen=True)
class TableOccurrence:
    table_id: str
    title: str
    page: int
    y0: float
    y1: float
    raw_line: str


@dataclass(frozen=True)
class DistinctTable:
    table_id: str
    title: str
    first_occurrence: TableOccurrence


def find_pdf(explicit: str | None = None) -> Path:
    if explicit:
        candidate = Path(explicit)
        if not candidate.exists():
            raise FileNotFoundError(f"PDF not found: {candidate}")
        return candidate
    pdfs = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(
            f"No PDF found under {INPUT_DIR}. Pass --pdf PATH or drop a manual there."
        )
    return pdfs[0]


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def should_skip_line(line: str) -> bool:
    if not line:
        return True
    if line in SKIP_LINES:
        return True
    if line.isdigit():
        return True
    return False


def iter_clean_lines(text: str) -> Iterable[str]:
    for raw in text.splitlines():
        line = normalize_line(raw)
        if should_skip_line(line):
            continue
        yield line


def find_line_bounds(page: fitz.Page, line: str) -> tuple[float, float] | None:
    rects = page.search_for(line)
    if rects:
        rect = rects[0]
        return rect.y0, rect.y1

    for block in page.get_text("blocks", sort=True):
        if len(block) < 7 or block[6] != TEXT_BLOCK:
            continue
        text = normalize_line(block[4])
        if line and line in text:
            return float(block[1]), float(block[3])
    return None


def collect_occurrences(doc: fitz.Document) -> list[TableOccurrence]:
    occurrences: list[TableOccurrence] = []
    for page_num in range(1, doc.page_count + 1):
        page = doc.load_page(page_num - 1)
        for line in iter_clean_lines(page.get_text("text")):
            match = TABLE_TITLE_RE.match(line)
            if not match:
                continue
            table_id = match.group(1)
            title = match.group(2).strip()
            bounds = find_line_bounds(page, line)
            if bounds is None:
                # Fallback keeps extraction moving even if exact search misses.
                y0, y1 = 0.0, 0.0
            else:
                y0, y1 = bounds
            occurrences.append(
                TableOccurrence(
                    table_id=table_id,
                    title=title,
                    page=page_num,
                    y0=y0,
                    y1=y1,
                    raw_line=line,
                )
            )
    occurrences.sort(key=lambda item: (item.page, item.y0, item.table_id))
    return occurrences


def distinct_tables(occurrences: list[TableOccurrence]) -> list[DistinctTable]:
    grouped: dict[str, list[TableOccurrence]] = {}
    for occ in occurrences:
        grouped.setdefault(occ.table_id, []).append(occ)

    chosen: list[DistinctTable] = []
    for table_id, occs in grouped.items():
        register_occs = [occ for occ in occs if REGISTER_TITLE_RE.search(occ.title)]
        if register_occs:
            best = min(register_occs, key=lambda occ: (occ.page, occ.y0, -len(occ.title)))
        else:
            best = occs[0]
        chosen.append(DistinctTable(table_id=table_id, title=best.title, first_occurrence=best))

    chosen.sort(key=lambda item: (item.first_occurrence.page, item.first_occurrence.y0, item.table_id))
    return chosen


def get_page(doc: fitz.Document, page_num: int, cache: dict[int, fitz.Page]) -> fitz.Page:
    page = cache.get(page_num)
    if page is None:
        page = doc.load_page(page_num - 1)
        cache[page_num] = page
    return page


def get_page_tables(
    doc: fitz.Document,
    page_num: int,
    table_cache: dict[int, list],
    page_cache: dict[int, fitz.Page],
) -> list:
    tables = table_cache.get(page_num)
    if tables is None:
        page = get_page(doc, page_num, page_cache)
        tables = sorted(page.find_tables().tables, key=lambda table: (table.bbox[1], table.bbox[0]))
        table_cache[page_num] = tables
    return tables


def get_page_text_blocks(
    doc: fitz.Document,
    page_num: int,
    block_cache: dict[int, list[tuple]],
    page_cache: dict[int, fitz.Page],
) -> list[tuple]:
    blocks = block_cache.get(page_num)
    if blocks is None:
        page = get_page(doc, page_num, page_cache)
        blocks = [block for block in page.get_text("blocks", sort=True) if len(block) >= 7 and block[6] == TEXT_BLOCK]
        block_cache[page_num] = blocks
    return blocks


def sanitize_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        line = normalize_line(line)
        if should_skip_line(line):
            continue
        if line.startswith("Figure "):
            continue
        cleaned.append(line)
    while cleaned and cleaned[0].startswith("Table "):
        cleaned.pop(0)
    return cleaned


def extract_raw_text(
    doc: fitz.Document,
    current: DistinctTable,
    next_occ: TableOccurrence | None,
    occ_by_id: dict[str, list[TableOccurrence]],
    block_cache: dict[int, list[tuple]],
    page_cache: dict[int, fitz.Page],
) -> tuple[int, int, str]:
    start_page = current.first_occurrence.page
    end_page = next_occ.page if next_occ is not None else doc.page_count
    chunks: list[str] = []

    per_page_occ = {occ.page: occ for occ in occ_by_id[current.table_id]}

    for page_num in range(start_page, end_page + 1):
        lower = 0.0
        upper = math.inf
        if page_num in per_page_occ:
            lower = per_page_occ[page_num].y1 + BOUND_MARGIN
        if next_occ is not None and page_num == next_occ.page:
            upper = max(next_occ.y0 - BOUND_MARGIN, lower)

        page_lines: list[str] = []
        for block in get_page_text_blocks(doc, page_num, block_cache, page_cache):
            x0, y0, x1, y1, text = block[:5]
            if y1 <= lower:
                continue
            if y0 >= upper:
                continue
            for raw_line in text.splitlines():
                line = normalize_line(raw_line)
                if not line:
                    continue
                page_lines.append(line)

        page_lines = sanitize_lines(page_lines)
        if page_lines:
            chunks.append("\n".join(page_lines))

    if next_occ is None:
        final_page = doc.page_count
    else:
        final_page = next_occ.page if next_occ.page > start_page else start_page
    return start_page, final_page, "\n\n".join(chunks).strip()


def dedupe_consecutive_rows(rows: list[list[str]]) -> list[list[str]]:
    deduped: list[list[str]] = []
    for row in rows:
        normalized = [normalize_line(cell) for cell in row]
        if deduped and deduped[-1] == normalized:
            continue
        deduped.append(normalized)
    return deduped


def extract_structured_rows(
    doc: fitz.Document,
    current: DistinctTable,
    next_occ: TableOccurrence | None,
    occ_by_id: dict[str, list[TableOccurrence]],
    table_cache: dict[int, list],
    page_cache: dict[int, fitz.Page],
) -> list[list[str]]:
    start_page = current.first_occurrence.page
    end_page = next_occ.page if next_occ is not None else doc.page_count
    rows: list[list[str]] = []
    per_page_occ = {occ.page: occ for occ in occ_by_id[current.table_id]}

    for page_num in range(start_page, end_page + 1):
        lower = 0.0
        upper = math.inf
        if page_num in per_page_occ:
            lower = per_page_occ[page_num].y1 + BOUND_MARGIN
        if next_occ is not None and page_num == next_occ.page:
            upper = max(next_occ.y0 - BOUND_MARGIN, lower)

        for table in get_page_tables(doc, page_num, table_cache, page_cache):
            bbox = table.bbox
            if bbox[3] <= lower:
                continue
            if bbox[1] >= upper:
                continue
            extracted = table.extract()
            if not extracted:
                continue
            for row in extracted:
                rows.append([normalize_line(cell or "") for cell in row])

    return dedupe_consecutive_rows(rows)


def write_raw_md(table_id: str, title: str, pages: tuple[int, int], text: str) -> Path:
    target = RAW_DIR / f"{table_id}.md"
    start_page, end_page = pages
    content = [
        f"# Table {table_id}",
        "",
        f"Title: {title}",
        f"Pages: {start_page}-{end_page}",
        "",
        "```text",
        text,
        "```",
        "",
    ]
    target.write_text("\n".join(content), encoding="utf-8")
    return target


def write_structured_csv(table_id: str, rows: list[list[str]]) -> Path | None:
    if not rows:
        return None
    target = CSV_DIR / f"{table_id}.csv"
    max_cols = max(len(row) for row in rows)
    fieldnames = [f"col_{idx}" for idx in range(1, max_cols + 1)]
    with target.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            padded = row + [""] * (max_cols - len(row))
            writer.writerow({name: value for name, value in zip(fieldnames, padded)})
    return target


def write_manifest(rows: list[dict[str, str]]) -> None:
    with MANIFEST_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "table_id",
                "title",
                "start_page",
                "end_page",
                "raw_md",
                "structured_csv",
                "structured_row_count",
                "raw_char_count",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default=None, help="path to the manual PDF")
    parser.add_argument("--max-pages", type=int, default=0, help="only scan the first N pages")
    args = parser.parse_args()

    try:
        pdf_path = find_pdf(args.pdf)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    if args.max_pages:
        doc.select(list(range(min(args.max_pages, doc.page_count))))
    occurrences = collect_occurrences(doc)
    all_distinct = distinct_tables(occurrences)
    occ_by_id: dict[str, list[TableOccurrence]] = {}
    for occ in occurrences:
        occ_by_id.setdefault(occ.table_id, []).append(occ)

    table_cache: dict[int, list] = {}
    block_cache: dict[int, list[tuple]] = {}
    page_cache: dict[int, fitz.Page] = {}

    manifest_rows: list[dict[str, str]] = []
    register_count = 0
    structured_count = 0

    for idx, current in enumerate(all_distinct):
        table_id = current.table_id
        title = current.title
        if not REGISTER_TITLE_RE.search(title):
            continue
        register_count += 1
        next_occ = all_distinct[idx + 1].first_occurrence if idx + 1 < len(all_distinct) else None

        start_page, end_page, raw_text = extract_raw_text(
            doc, current, next_occ, occ_by_id, block_cache, page_cache
        )
        raw_path = write_raw_md(table_id, title, (start_page, end_page), raw_text)

        structured_rows = extract_structured_rows(
            doc, current, next_occ, occ_by_id, table_cache, page_cache
        )
        csv_path = write_structured_csv(table_id, structured_rows)
        if csv_path is not None:
            structured_count += 1

        manifest_rows.append(
            {
                "table_id": table_id,
                "title": title,
                "start_page": str(start_page),
                "end_page": str(end_page),
                "raw_md": raw_path.relative_to(ROOT).as_posix(),
                "structured_csv": csv_path.relative_to(ROOT).as_posix() if csv_path else "",
                "structured_row_count": str(len(structured_rows)),
                "raw_char_count": str(len(raw_text)),
            }
        )

    write_manifest(manifest_rows)
    print(f"Register tables: {register_count}")
    print(f"Structured CSV emitted: {structured_count}")
    print(f"Manifest: {MANIFEST_CSV.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
