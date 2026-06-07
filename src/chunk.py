"""Stage 2 — Chunking.

Splits documents into token-bounded chunks measured with the *actual*
all-MiniLM-L6-v2 tokenizer, so "tokens" here means exactly what the embedding
model will see.

Important model fact: all-MiniLM-L6-v2 has a max sequence length of 256
word-piece tokens. Anything longer is silently truncated at embed time, so a
chunk only "works with" the model if it fits in 256 tokens. We therefore clamp
every chunk-size target to MODEL_MAX.

Chunking is segment-aware: text is first broken into natural segments
(paragraphs, then sentences/lines for oversized ones), and segments are packed
greedily up to the token budget. The listing sources (event calendars /
attraction lists) use no overlap so each event/attraction stays self-contained.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from transformers import AutoTokenizer

from scrape import Document

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_MAX = 256  # all-MiniLM-L6-v2 hard truncation limit (word-piece tokens)

# Small targets so each chunk is only a few lines (one or two venues/events),
# which keeps retrieval focused. Well under the 256-token model limit.
CHUNK_CONFIG = {
    "listing": {"target": 80, "overlap": 0},  # event/attraction lists
}

_tokenizer = None


def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    return _tokenizer


def n_tokens(text: str) -> int:
    # add_special_tokens=False -> count content tokens only (no [CLS]/[SEP]).
    return len(get_tokenizer().encode(text, add_special_tokens=False))


@dataclass
class Chunk:
    chunk_id: str
    source_id: int
    source_name: str
    source_url: str
    text: str
    n_tokens: int = 0
    metadata: dict = field(default_factory=dict)


def _split_segments(text: str, max_seg: int) -> list[str]:
    """Break text into paragraphs, then split any paragraph longer than
    ``max_seg`` tokens into sentence-ish pieces so no single segment blows past
    the chunk target."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    segments: list[str] = []
    for p in paras:
        if n_tokens(p) <= max_seg:
            segments.append(p)
            continue
        # Oversized paragraph: split on sentence boundaries / newlines.
        pieces = re.split(r"(?<=[.!?])\s+|\n", p)
        buf = ""
        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            candidate = f"{buf} {piece}".strip()
            if n_tokens(candidate) > max_seg and buf:
                segments.append(buf)
                buf = piece
            else:
                buf = candidate
        if buf:
            segments.append(buf)
    return segments


def chunk_document(doc: Document) -> list[Chunk]:
    cfg = CHUNK_CONFIG[doc.source.kind]
    target = min(cfg["target"], MODEL_MAX)
    overlap = min(cfg["overlap"], target // 2)

    segments = _split_segments(doc.text, target)
    chunks: list[Chunk] = []
    cur: list[str] = []
    cur_tokens = 0
    idx = 0

    def flush():
        nonlocal cur, cur_tokens, idx
        if not cur:
            return
        text = "\n\n".join(cur).strip()
        chunks.append(Chunk(
            chunk_id=f"src{doc.source.id}-{idx:03d}",
            source_id=doc.source.id,
            source_name=doc.source.name,
            source_url=doc.source.url,
            text=text,
            n_tokens=n_tokens(text),
            metadata={"kind": doc.source.kind, "description": doc.source.description},
        ))
        idx += 1

    for seg in segments:
        seg_tokens = n_tokens(seg)
        if cur and cur_tokens + seg_tokens > target:
            flush()
            if overlap > 0:
                # Carry the tail segment(s) forward as overlap context.
                carry, carry_tokens = [], 0
                for s in reversed(cur):
                    t = n_tokens(s)
                    if carry_tokens + t > overlap:
                        break
                    carry.insert(0, s)
                    carry_tokens += t
                cur, cur_tokens = carry, carry_tokens
            else:
                cur, cur_tokens = [], 0
        cur.append(seg)
        cur_tokens += seg_tokens
    flush()
    return chunks


def chunk_all(docs: list[Document]) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for doc in docs:
        if not doc.ok or not doc.text:
            continue
        cs = chunk_document(doc)
        print(f"  ({doc.source.id:>2}) {doc.source.name:<24} -> {len(cs)} chunks")
        all_chunks.extend(cs)
    return all_chunks
