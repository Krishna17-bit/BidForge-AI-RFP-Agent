from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .document_loader import LoadedDocument


@dataclass
class Chunk:
    chunk_id: str
    document: str
    page: int
    text: str


class EvidenceIndex:
    def __init__(self, docs: list[LoadedDocument], chunk_size: int = 1100, overlap: int = 160):
        self.chunks: list[Chunk] = []
        for doc in docs:
            for page in doc.pages:
                page_num = int(page.get("page", 1))
                for idx, chunk_text in enumerate(self._chunk(page.get("text", ""), chunk_size, overlap)):
                    self.chunks.append(
                        Chunk(
                            chunk_id=f"{doc.name}:p{page_num}:c{idx}",
                            document=doc.name,
                            page=page_num,
                            text=chunk_text,
                        )
                    )
        corpus = [c.text for c in self.chunks] or [""]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=24000)
        self.matrix = self.vectorizer.fit_transform(corpus)

    @staticmethod
    def _chunk(text: str, chunk_size: int, overlap: int) -> Iterable[str]:
        cleaned = re.sub(r"\n{3,}", "\n\n", text or "").strip()
        if not cleaned:
            return []
        chunks = []
        start = 0
        while start < len(cleaned):
            end = min(len(cleaned), start + chunk_size)
            # Try not to split mid sentence/line.
            soft_end = max(cleaned.rfind("\n", start, end), cleaned.rfind(". ", start, end))
            if soft_end > start + int(chunk_size * 0.55):
                end = soft_end + 1
            chunks.append(cleaned[start:end].strip())
            if end >= len(cleaned):
                break
            start = max(0, end - overlap)
        return chunks

    def search(self, query: str, k: int = 5) -> list[dict]:
        if not self.chunks or not query.strip():
            return []
        q = self.vectorizer.transform([query])
        scores = cosine_similarity(q, self.matrix).reshape(-1)
        top_idx = np.argsort(scores)[::-1][:k]
        results = []
        for idx in top_idx:
            score = float(scores[idx])
            if score <= 0:
                continue
            c = self.chunks[int(idx)]
            results.append(
                {
                    "chunk_id": c.chunk_id,
                    "document": c.document,
                    "page": c.page,
                    "score": round(score, 4),
                    "text": c.text[:900],
                }
            )
        return results

    def top_context(self, query: str, k: int = 8, max_chars: int = 9000) -> str:
        blocks = []
        used = 0
        for r in self.search(query, k=k):
            block = f"[Evidence: {r['document']} p.{r['page']} score={r['score']}]\n{r['text']}"
            if used + len(block) > max_chars:
                break
            blocks.append(block)
            used += len(block)
        return "\n\n".join(blocks)
