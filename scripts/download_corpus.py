"""Download the default demo corpus listed in data/sources.yaml into data/raw/.

Usage:  python scripts/download_corpus.py
Entries without a `url` (or whose download fails) are printed with their landing page
so you can save the PDF manually under the listed file name.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    docs = yaml.safe_load((ROOT / "data" / "sources.yaml").read_text())["documents"]
    manual = []
    headers = {"User-Agent": "Mozilla/5.0 (rag-lab corpus downloader)"}
    with httpx.Client(follow_redirects=True, timeout=60, headers=headers) as client:
        for d in docs:
            dest = RAW / d["file"]
            if dest.exists():
                print(f"  OK  {d['file']} (already present)")
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
                print(f"  OK  {d['file']} ({len(r.content) / 1e6:.1f} MB)")
            except Exception as e:  # noqa: BLE001
                print(f"  FAIL {d['file']}: {e}")
                manual.append(d)

    if manual:
        print("\nSave these manually into data/raw/ (exact file name on the left):")
        for d in manual:
            print(f"  {d['file']:<26} <- {d['page']}")
    print(f"\nPDFs in data/raw: {len(list(RAW.glob('*.pdf')))}")


if __name__ == "__main__":
    main()
