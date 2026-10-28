"""Ingest guards: duplicate PDFs skipped, empty (scanned) PDFs reported, no-PDF folder fails."""

import shutil
from pathlib import Path

import pymupdf
import pytest

from raglab.config import Config
from raglab.ingest.parse import load_corpus
from raglab.pipeline import ingest


def _make_pdf(path: Path, text: str | None) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    doc.save(path)


def test_duplicate_pdf_under_new_name_is_skipped(tmp_path, caplog):
    _make_pdf(tmp_path / "a_basel.pdf", "Output floor is 72.5 percent.")
    shutil.copy(tmp_path / "a_basel.pdf", tmp_path / "b_copy.pdf")
    pages = load_corpus(tmp_path)
    assert len(pages) == 1
    assert "identical to a_basel.pdf" in caplog.text


def test_pdf_without_text_is_reported(tmp_path, caplog):
    _make_pdf(tmp_path / "scan.pdf", None)
    assert load_corpus(tmp_path) == []
    assert "needs OCR" in caplog.text


def test_ingest_with_no_pdfs_raises(tmp_path):
    cfg = Config.model_validate({"corpus": {"raw_dir": str(tmp_path)}})
    with pytest.raises(FileNotFoundError):
        ingest(cfg)
