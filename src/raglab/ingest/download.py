"""Download the default demo corpus listed in data/sources.yaml into data/raw/.

Entries without a `url` (or whose download fails) are reported with their landing page
so a human can save the PDF manually under the listed file name.
"""

from __future__ import annotations

import logging

import httpx
import yaml

from raglab.config import REPO_ROOT

log = logging.getLogger(__name__)
RAW = REPO_ROOT / "data" / "raw"
SOURCES = REPO_ROOT / "data" / "sources.yaml"


def download_corpus() -> list[str]:
    """Fetch every listed document that has a URL. Returns file names still missing."""
    RAW.mkdir(parents=True, exist_ok=True)
    docs = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))["documents"]
    manual = []
    headers = {"User-Agent": "Mozilla/5.0 (rag-lab corpus downloader)"}
    with httpx.Client(follow_redirects=True, timeout=60, headers=headers) as client:
        for d in docs:
            dest = RAW / d["file"]
            if dest.exists():
                log.info("OK   %s (already present)", d["file"])
                continue
            url = d.get("url")
            if not url:
                manual.append(d)
                continue
            try:
                r = client.get(url)
                r.raise_for_status()
                if not r.content.startswith(b"%PDF"):
                    raise ValueError("response is not a PDF")
                dest.write_bytes(r.content)
                log.info("OK   %s (%.1f MB)", d["file"], len(r.content) / 1e6)
            except Exception as e:  # noqa: BLE001 - report and continue with the rest
                log.warning("FAIL %s: %s", d["file"], e)
                manual.append(d)

    for d in manual:
        log.warning("save manually into data/raw/  %-26s <- %s", d["file"], d["page"])
    log.info("PDFs in data/raw: %d", len(list(RAW.glob("*.pdf"))))
    return [d["file"] for d in manual]
