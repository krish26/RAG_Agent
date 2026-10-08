"""
Step 1 of the D&D rules agent: read a PDF and split it into chunks.

Run:   python 01_ingest.py data/srd.pdf
See one page's chunks in full:
       python 01_ingest.py data/srd.pdf 77
Out:   data/chunks.json

The first run on the full SRD takes a few minutes.
"""

import json
import re
import sys
from pathlib import Path

import pymupdf4llm  # turns PDF pages into Markdown (handles columns and tables)

# Target size of a text chunk, in characters. You will tune this later.
CHUNK_SIZE = 1000

# A table bigger than this is split into several chunks by rows,
# and every piece gets the table's header rows repeated on top.
MAX_TABLE_SIZE = 1500

# The page footer of the SRD, e.g. "**77** System Reference Document 5.2.1"
FOOTER = re.compile(r"^(\*\*\d+\*\*\s*)?System Reference Document[\d. ]*(\s*\*\*\d+\*\*)?\s*$")


def pdf_to_pages(pdf_path):
    """Return [{"page": number, "text": markdown}] for every page.

    pymupdf4llm does two jobs for us here:
      - it reads a two-column page in the right order (left column, then right)
      - it turns tables into Markdown tables, one row per line
    """
    pages = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True, show_progress=True)
    result = []
    for number, page in enumerate(pages, start=1):
        lines = [l for l in page["text"].splitlines() if not FOOTER.match(l.strip())]
        text = "\n".join(lines).strip()
        if text:
            result.append({"page": number, "text": text})
    return result


def split_blocks(markdown):
    """Split a page into blocks: a heading, a paragraph, a list item, or a whole table."""
    return [b.strip() for b in re.split(r"\n\s*\n", markdown) if b.strip()]


def is_table(block):
    return block.startswith("|")


def is_heading(block):
    return block.startswith("#") and "\n" not in block


def clean_heading(block):
    text = re.sub(r"<[^>]+>", "", block.lstrip("#"))  # drop tags like <u>
    return text.replace("*", "").replace("_", "").strip()


def split_table(block, max_size=MAX_TABLE_SIZE):
    """Keep a small table whole. Split a big one by rows, repeating its header.

    Without the header, a row like "|5|+3|Memorize Spell|4|9|4|3|2|" is just
    numbers. With it, every piece still says what each column means.
    """
    if len(block) <= max_size:
        return [block]

    rows = block.splitlines()
    # header = everything up to and including the |---|---| separator line
    sep = next((i for i, r in enumerate(rows) if set(r) <= set("|-: ")), 0)
    header, body = rows[: sep + 1], rows[sep + 1 :]

    pieces, current = [], []
    for row in body:
        if current and len("\n".join(header + current)) + len(row) > max_size:
            pieces.append("\n".join(header + current))
            current = []
        current.append(row)
    if current:
        pieces.append("\n".join(header + current))
    return pieces


def make_chunks(pages, source):
    """Walk through the document and build chunks.

    Three rules:
      1. Remember the current section heading and put it on top of every
         chunk, so a chunk about spell slots still says "Wizard".
      2. Never cut a table in the middle without repeating its header.
      3. Group normal text until it reaches CHUNK_SIZE.
    """
    chunks = []
    section = ""      # last big heading seen, e.g. "Wizard"
    subsection = ""   # last small heading seen, e.g. "Level 1: Spellcasting"

    def add(page, text):
        title = " > ".join(t for t in (section, subsection) if t)
        chunks.append(
            {
                "id": f"{Path(source).stem}-p{page}-c{len(chunks)}",
                "source": source,
                "page": page,
                "section": title,
                "text": f"[{title}]\n{text}" if title else text,
            }
        )

    for page in pages:
        buffer = []

        def flush():
            if buffer:
                add(page["page"], "\n\n".join(buffer))
                buffer.clear()

        for block in split_blocks(page["text"]):
            if is_heading(block):
                flush()
                level = len(block) - len(block.lstrip("#"))
                if level <= 2:
                    section, subsection = clean_heading(block), ""
                else:
                    subsection = clean_heading(block)
            elif is_table(block):
                flush()
                for piece in split_table(block):
                    add(page["page"], piece)
            else:
                if buffer and len("\n\n".join(buffer)) + len(block) > CHUNK_SIZE:
                    flush()
                buffer.append(block)
        flush()

    return chunks


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit("Usage: python 01_ingest.py path/to/file.pdf [page_number]")

    pdf_path = Path(sys.argv[1])
    show_page = int(sys.argv[2]) if len(sys.argv) == 3 else None

    pages = pdf_to_pages(pdf_path)
    if not pages:
        sys.exit("No text found in this PDF.")

    chunks = make_chunks(pages, pdf_path.name)

    out_path = pdf_path.parent / "chunks.json"
    out_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

    lengths = [len(c["text"]) for c in chunks]
    tables = sum(1 for c in chunks if "\n|" in c["text"])
    print(f"\nPages with text : {len(pages)}")
    print(f"Chunks created  : {len(chunks)}  ({tables} of them contain a table)")
    print(f"Chunk length    : min {min(lengths)}, avg {sum(lengths) // len(lengths)}, max {max(lengths)}")
    print(f"Saved to        : {out_path}")

    if show_page is not None:
        print(f"\n--- every chunk from PDF page {show_page}, in full ---")
        for chunk in chunks:
            if chunk["page"] == show_page:
                print(f"\n({chunk['id']})\n{chunk['text']}")
    else:
        print("\nTip: add a page number to see that page's chunks in full,")
        print("     e.g.  python 01_ingest.py data/srd.pdf 77")


if __name__ == "__main__":
    main()
