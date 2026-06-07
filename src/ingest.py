"""Milestone 3 entry point — Ingestion + Chunking.

Run from the project root:
    .venv\\Scripts\\python.exe src\\ingest.py

Pipeline:
    scrape sources -> save raw text to documents/ -> chunk -> save chunks.json
    -> print 5 random chunks.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

# Allow running as a plain script (so sibling imports resolve).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from chunk import chunk_all  # noqa: E402
from scrape import scrape_all  # noqa: E402
from sources import SOURCES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "documents"
CHUNKS_FILE = ROOT / "chunks.json"


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")


def main(seed: int = 42, n_preview: int = 5) -> None:
    DOCS_DIR.mkdir(exist_ok=True)

    print("== Stage 1: Scraping sources ==")
    docs = scrape_all(SOURCES)

    ok_docs = [d for d in docs if d.ok and d.text]
    failed = [d for d in docs if not (d.ok and d.text)]

    # Persist the raw text of every source we could fetch.
    for d in ok_docs:
        path = DOCS_DIR / f"{d.source.id:02d}-{_slug(d.source.name)}.txt"
        path.write_text(d.text, encoding="utf-8")

    print(f"\n  Fetched {len(ok_docs)}/{len(docs)} sources "
          f"({sum(d.n_chars for d in ok_docs):,} chars). "
          f"Raw text saved to documents/")
    if failed:
        print("  Could not scrape:")
        for d in failed:
            print(f"    - ({d.source.id}) {d.source.name}: {d.note}")

    print("\n== Stage 2: Chunking ==")
    chunks = chunk_all(ok_docs)

    if not chunks:
        print("\nNo chunks produced — nothing scraped successfully.")
        return

    # Persist chunks for the embedding/retrieval milestone.
    CHUNKS_FILE.write_text(
        json.dumps([c.__dict__ for c in chunks], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    sizes = [c.n_tokens for c in chunks]
    print(f"\n  Total: {len(chunks)} chunks across {len(ok_docs)} documents.")
    print(f"  Tokens/chunk: min={min(sizes)} max={max(sizes)} "
          f"avg={sum(sizes)/len(sizes):.0f} (model max 256).")
    print(f"  Chunks saved to {CHUNKS_FILE.name}")

    # ---- Print N random chunks ----
    rng = random.Random(seed)
    sample = rng.sample(chunks, min(n_preview, len(chunks)))
    print(f"\n== {len(sample)} random chunks (seed={seed}) ==")
    for i, c in enumerate(sample, 1):
        print("\n" + "-" * 78)
        print(f"[{i}] {c.chunk_id} | {c.source_name} | {c.n_tokens} tokens")
        print(f"    {c.source_url}")
        print("-" * 78)
        print(c.text)


if __name__ == "__main__":
    main()
