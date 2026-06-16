from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Optional, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .document_loader import LoadedDocument
from .config import settings

@dataclass
class Chunk:
    chunk_id: str
    document: str
    page: int
    text: str
    embedding: Optional[list[float]] = None

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
        
        # Build TF-IDF local index as base fallback
        corpus = [c.text for c in self.chunks] or [""]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=24000)
        self.matrix = self.vectorizer.fit_transform(corpus)
        
        # Calculate dense embeddings if API keys are active
        self.has_dense = False
        self.dense_matrix = None
        self._build_dense_index()

    def _build_dense_index(self):
        # Prevent remote calls if mock mode is on
        if settings.mock_mode:
            return
            
        if settings.gemini_api_key:
            try:
                self._build_gemini_dense()
                self.has_dense = True
            except Exception as e:
                print(f"Could not build Gemini dense index: {e}")
        elif settings.openai_api_key:
            try:
                self._build_openai_dense()
                self.has_dense = True
            except Exception as e:
                print(f"Could not build OpenAI dense index: {e}")

    def _build_gemini_dense(self):
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)
        
        embeddings = []
        for chunk in self.chunks:
            res = client.models.embed_content(
                model="text-embedding-004",
                contents=chunk.text
            )
            val = res.embeddings[0].values
            chunk.embedding = val
            embeddings.append(val)
            
        if embeddings:
            self.dense_matrix = np.array(embeddings)

    def _build_openai_dense(self):
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        
        embeddings = []
        for chunk in self.chunks:
            res = client.embeddings.create(
                model="text-embedding-3-small",
                input=chunk.text
            )
            val = res.data[0].embedding
            chunk.embedding = val
            embeddings.append(val)
            
        if embeddings:
            self.dense_matrix = np.array(embeddings)

    @staticmethod
    def _chunk(text: str, chunk_size: int, overlap: int) -> Iterable[str]:
        cleaned = re.sub(r"\n{3,}", "\n\n", text or "").strip()
        if not cleaned:
            return []
        chunks = []
        start = 0
        while start < len(cleaned):
            end = min(len(cleaned), start + chunk_size)
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
            
        # Dense Embedding Search
        if self.has_dense and self.dense_matrix is not None:
            try:
                q_emb = self._get_query_embedding(query)
                if q_emb is not None:
                    q_vector = np.array(q_emb).reshape(1, -1)
                    scores = cosine_similarity(q_vector, self.dense_matrix).reshape(-1)
                    return self._score_results(scores, k)
            except Exception as e:
                print(f"Dense search failed, falling back to TF-IDF: {e}")

        # Sparse TF-IDF Search (Default Fallback)
        q = self.vectorizer.transform([query])
        scores = cosine_similarity(q, self.matrix).reshape(-1)
        return self._score_results(scores, k)

    def _get_query_embedding(self, query: str) -> Optional[list[float]]:
        if settings.gemini_api_key:
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            res = client.models.embed_content(
                model="text-embedding-004",
                contents=query
            )
            return res.embeddings[0].values
        elif settings.openai_api_key:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            res = client.embeddings.create(
                model="text-embedding-3-small",
                input=query
            )
            return res.data[0].embedding
        return None

    def _score_results(self, scores: np.ndarray, k: int) -> list[dict]:
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
