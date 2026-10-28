"""PDF -> pages of text. Baseline uses PyMuPDF plain text extraction.

Known weakness (deliberately left for later experiments): tables come out as
flattened text. Layout-aware parsing (e.g. Docling) is a later benchmark arm.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

import pymupdf as fitz
import yaml

from raglab.models import Page

log = logging.getLogger(__name__)


def _clean(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_pdf(path: Path, doc_id: str, title: str) -> list[Page]:
    pages: list[Page] = []
    with fitz.open(path) as doc:
        for i, pg in enumerate(doc, start=1):
            text = _clean(pg.get_text("text"))
            if text:
                pages.append(Page(doc_id=doc_id, title=title, page=i, text=text))
    return pages


def load_corpus(raw_dir: Path, sources_file: Path | None = None) -> list[Page]:
    """Parse every PDF in raw_dir. Titles come from data/sources.yaml when listed there,
    so user-supplied PDFs ("bring your own documents") work without any registration."""
    titles: dict[str, tuple[str, str]] = {}
    if sources_file and sources_file.exists():
        for d in yaml.safe_load(sources_file.read_text())["documents"]:
            titles[d["file"]] = (d["id"], d["title"])

    pages: list[Page] = []
    seen: dict[str, str] = {}  # content hash -> first file name
    for pdf in sorted(raw_dir.glob("*.pdf")):
        # Same bytes under a different file name = duplicate; indexing it twice
        # would waste top-k slots on identical chunks.
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if digest in seen:
            log.warning("skipping %s: identical to %s", pdf.name, seen[digest])
            continue
        seen[digest] = pdf.name
        doc_id, title = titles.get(pdf.name, (pdf.stem, pdf.stem.replace("_", " ")))
        doc_pages = parse_pdf(pdf, doc_id, title)
        if not doc_pages:
            log.warning("%s: no extractable text (scanned PDF? needs OCR) - skipped", pdf.name)
        else:
            log.info("parsed %s: %d pages", pdf.name, len(doc_pages))
        pages.extend(doc_pages)
    return pages
