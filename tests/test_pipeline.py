"""Offline tests: no API keys, no network. Uses the hash embedder + in-memory Qdrant."""

from pathlib import Path

import pymupdf as fitz

from raglab.chunking.fixed import FixedChunker
from raglab.embeddings import HashEmbedder
from raglab.generation.generator import build_context
from raglab.ingest.parse import load_corpus
from raglab.models import Page
from raglab.retrieval.vector import VectorRetriever
from raglab.store.qdrant_store import QdrantStore, make_client


def test_chunker_respects_size_and_overlap():
    text = ("This is a sentence about capital adequacy. " * 100).strip()
    chunks = FixedChunker(300, 50).chunk([Page("d", "Doc", 1, text)])
    assert len(chunks) > 1
    assert all(len(c.text) <= 300 for c in chunks)
    assert chunks[0].chunk_id == "d:p1:c0"


def test_short_page_is_single_chunk():
    chunks = FixedChunker(300, 50).chunk([Page("d", "Doc", 3, "short page")])
    assert len(chunks) == 1 and chunks[0].page == 3


def test_parse_pdf_roundtrip(tmp_path: Path):
    pdf = tmp_path / "sample.pdf"
    doc = fitz.open()
    for line in ["Leverage ratio minimum is three percent.", "Output floor is 72.5 percent."]:
        doc.new_page().insert_text((72, 72), line)
    doc.save(pdf)
    pages = load_corpus(tmp_path)
    assert [p.page for p in pages] == [1, 2]
    assert "72.5" in pages[1].text


def test_retrieval_finds_relevant_chunk():
    pages = [
        Page("a", "Basel", 1, "The output floor is set at 72.5 percent of standardised RWA."),
        Page("b", "TRM", 1, "Banks should maintain incident response plans for cyber attacks."),
    ]
    chunks = FixedChunker(500, 50).chunk(pages)
    emb = HashEmbedder()
    store = QdrantStore(make_client(None, None, None), "test")
    store.recreate(emb.dim)
    store.upsert(chunks, emb.embed_documents([c.text for c in chunks]))
    hits = VectorRetriever(emb, store).retrieve("what is the output floor percent", 1)
    assert hits[0].chunk.doc_id == "a"
    assert "[1] (source: Basel, page 1)" in build_context(hits)
