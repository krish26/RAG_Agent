"""
A small table store, built from the table chunks in data/chunks.json.

Semantic search is bad at tables (we measured it). So instead of searching
tables by meaning, the agent can list them by name and read their rows
directly, the way you would flip to a table in the book.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

CHUNKS_FILE = Path("data/chunks.json")


def clean(cell):
    """Remove Markdown decoration: **bold**, _italic_, <br> line breaks."""
    cell = re.sub(r"<br\s*/?>", " ", cell)
    cell = re.sub(r"<[^>]+>", "", cell)
    return " ".join(cell.replace("**", "").replace("_", "").split())


def is_bold_row(line):
    cells = [c.strip() for c in line.strip().strip("|").split("|") if c.strip()]
    return bool(cells) and all(c.startswith("**") for c in cells)


def parse_rows(lines):
    return [[clean(c) for c in line.strip().strip("|").split("|")] for line in lines]


@lru_cache(maxsize=1)
def load_tables():
    """Return {table name: {"page", "header", "rows"}}.

    A big table was split into several chunks, each with the header repeated.
    Pieces with the same section, page and header are glued back together.
    """
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    tables = {}
    for chunk in chunks:
        lines = [l for l in chunk["text"].splitlines() if l.startswith("|")]
        sep = next((i for i, l in enumerate(lines) if set(l) <= set("|-: ")), None)
        if sep is None:
            continue
        body = lines[sep + 1 :]
        # Some tables have a second header row below the |---| line
        # (the Wizard table's "Level | Bonus | ... | 1 | 2 | 3"). In the
        # Markdown every cell of a header row is **bold**, so we spot it that way.
        extra = 0
        while extra < len(body) and is_bold_row(body[extra]):
            extra += 1
        header = parse_rows(lines[:sep] + body[:extra])
        rows = parse_rows(body[extra:])
        name = f"{chunk['section'] or 'Untitled'} (page {chunk['page']})"
        name = clean(name)
        if name in tables and tables[name]["header"] == header:
            tables[name]["rows"].extend(rows)
        else:
            if name in tables:  # a second, different table under the same heading
                name = f"{name} #{sum(n.startswith(name) for n in tables) + 1}"
            tables[name] = {"page": chunk["page"], "header": header, "rows": rows}
    return tables


def list_tables(keyword):
    """Names of tables whose name or column headers contain the keyword."""
    keyword = keyword.lower()
    found = []
    for name, t in load_tables().items():
        header_text = " ".join(" ".join(r) for r in t["header"]).lower()
        if keyword in name.lower() or keyword in header_text:
            found.append(name)
    return found


def format_rows(header, rows):
    return "\n".join(" | ".join(r) for r in header + rows)


def read_table(name, row_contains="", max_rows=40):
    """Header + rows of one table. If row_contains is given, only rows where
    some cell matches it (whole cell, or whole word inside a cell)."""
    tables = load_tables()
    if name not in tables:
        close = [n for n in tables if name.lower() in n.lower()]
        if len(close) == 1:
            name = close[0]
        else:
            return None, close[:10]
    t = tables[name]
    rows = t["rows"]
    if row_contains:
        needle = row_contains.lower().strip()
        pattern = re.compile(r"(?<![\w.+-])" + re.escape(needle) + r"(?![\w])")
        # Best match: the first column equals the search (e.g. Level "5", Name "Rapier").
        first_cell = [r for r in rows if r and r[0].lower() == needle]
        rows = first_cell or [
            r for r in rows if any(c.lower() == needle or pattern.search(c.lower()) for c in r)
        ]
    return {"name": name, "page": t["page"], "text": format_rows(t["header"], rows[:max_rows]),
            "rows_shown": min(len(rows), max_rows), "rows_total": len(t["rows"])}, None
