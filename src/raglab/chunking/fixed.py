"""Baseline chunker: fixed-size character windows with overlap, per page.

Windows prefer to end at a paragraph or sentence break so chunks don't cut words.
Chunking per page keeps citations exact; the cost is that content spanning a page
break is split — a known weakness the parent-child / recursive strategies will target.
"""

from __future__ import annotations

from raglab.models import Chunk, Page

_BREAKS = ("\n\n", ". ", "\n", " ")


class FixedChunker:
    def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 200):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.size = chunk_size
        self.overlap = chunk_overlap

    def _split(self, text: str) -> list[str]:
        if len(text) <= self.size:
            return [text]
        out, start = [], 0
        while start < len(text):
            end = min(start + self.size, len(text))
            if end < len(text):
                # back off to the nearest natural break in the last 30% of the window
                floor = start + int(self.size * 0.7)
                for b in _BREAKS:
                    idx = text.rfind(b, floor, end)
                    if idx != -1:
                        end = idx + len(b)
                        break
            piece = text[start:end].strip()
            if piece:
                out.append(piece)
            if end >= len(text):
                break
            start = max(end - self.overlap, start + 1)
        return out

    def chunk(self, pages: list[Page]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for p in pages:
            for j, piece in enumerate(self._split(p.text)):
                chunks.append(
                    Chunk(
                        chunk_id=f"{p.doc_id}:p{p.page}:c{j}",
                        doc_id=p.doc_id,
                        title=p.title,
                        page=p.page,
                        text=piece,
                    )
                )
        return chunks
