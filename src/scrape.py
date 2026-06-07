"""Stage 1 — Document ingestion.

Fetch each source URL and reduce it to clean plain text:
  - Static HTML sites: strip boilerplate (nav/script/style/footer) and keep the
    main textual content.
  - Failures (anti-bot 403s, JS-only SPAs with no static text): reported, not
    fatal — the pipeline continues with whatever it could fetch.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from sources import Source

# A realistic browser User-Agent. Some sites still block bot traffic regardless
# (those return 403 and are reported as skipped, not fatal).
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 25


@dataclass
class Document:
    source: Source
    text: str
    ok: bool
    note: str = ""

    @property
    def n_chars(self) -> int:
        return len(self.text)


# UI / navigation boilerplate that carries no information about places or
# events. Matched after lowercasing and stripping trailing ">>>".
_BOILERPLATE_EXACT = {
    "share", "details", "map", "save", "website", "explore", "upcoming",
    "credit", "open in google maps", "full event calendar", "see & do",
    "more things to do", "choose your experience", "plan your trip",
    "local experiences", "directions", "menu", "home",
}
# Lines starting with any of these are call-to-action / nav labels.
_BOILERPLATE_PREFIXES = (
    "learn more", "continue reading", "read more", "view more",
    "submit your event", "submit an event", "add your event",
    "subscribe to", "filter by", "get updated", "do you own a business",
)
_BOILERPLATE_PATTERNS = [
    re.compile(r"^results\s+\d+\s*-\s*\d+\s+of\s+\d+", re.I),
    re.compile(r"business listing guidelines", re.I),
    re.compile(r"e-?newsletter", re.I),
]


def _is_boilerplate(line: str) -> bool:
    s = re.sub(r"\s*>>>+\s*$", "", line.strip()).strip()
    # Lines with no alphanumeric content (stray ">>>", "|", zero-width chars).
    if not re.sub(r"[\W_]", "", s):
        return True
    norm = s.lower().strip(" .|›»")
    if norm in _BOILERPLATE_EXACT:
        return True
    if any(norm.startswith(p) for p in _BOILERPLATE_PREFIXES):
        return True
    return any(p.search(s) for p in _BOILERPLATE_PATTERNS)


def _strip_boilerplate(text: str) -> str:
    """Drop nav/CTA junk lines, then de-duplicate immediately repeated lines
    (listing pages echo each venue name twice)."""
    kept: list[str] = []
    prev = None
    for ln in text.splitlines():
        if ln and _is_boilerplate(ln):
            continue
        if ln and ln == prev:  # collapse "Name\nName" duplicates
            continue
        kept.append(re.sub(r"\s*>>>+\s*$", "", ln).rstrip())
        prev = ln if ln else prev
    return _collapse("\n".join(kept))


def _collapse(text: str) -> str:
    """Normalize whitespace while preserving paragraph (blank-line) breaks."""
    # Collapse runs of spaces/tabs, trim each line, drop empty-line runs to one.
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    out: list[str] = []
    blank = False
    for ln in lines:
        if ln:
            out.append(ln)
            blank = False
        elif not blank:
            out.append("")
            blank = True
    return "\n".join(out).strip()


def _html_to_text(html: bytes | str) -> str:
    # Pass raw bytes so BeautifulSoup detects the charset from the page's own
    # <meta> tag — requests guesses wrong on some sites (e.g. visit.cstx.gov),
    # which otherwise mangles UTF-8 punctuation/accents into "â¦", "Ã©", etc.
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header",
                     "form", "svg", "iframe", "aside"]):
        tag.decompose()
    # Prefer a main/article container if one exists; else fall back to body.
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(separator="\n")
    return _strip_boilerplate(_collapse(text))


def _fetch_html(source: Source) -> Document:
    try:
        r = requests.get(source.url, headers=HEADERS, timeout=TIMEOUT)
    except Exception as e:  # noqa: BLE001
        return Document(source, "", False, f"request error: {e!r}")

    if r.status_code != 200:
        return Document(source, "", False,
                        f"HTTP {r.status_code} — likely anti-bot block")

    text = _html_to_text(r.content)
    if len(text) < 200:
        return Document(source, text, False,
                        f"only {len(text)} chars extracted — likely a "
                        "JS-rendered page with no static content")
    return Document(source, text, True, f"{len(text)} chars")


def scrape(source: Source) -> Document:
    return _fetch_html(source)


def scrape_all(sources: list[Source], polite_delay: float = 1.0) -> list[Document]:
    docs: list[Document] = []
    for s in sources:
        doc = scrape(s)
        status = "OK " if doc.ok else "SKIP"
        print(f"  [{status}] ({s.id:>2}) {s.name:<24} {doc.note}")
        docs.append(doc)
        time.sleep(polite_delay)  # be polite between requests
    return docs
