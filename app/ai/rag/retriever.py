"""
FAISS Vector Store & Retriever
================================
Builds a FAISS index from document chunks and retrieves the
top-k most semantically similar chunks for a query.
"""

import os
from typing import List, Tuple

import faiss
import numpy as np
from loguru import logger

from app.ai.embeddings.embedding_engine import EmbeddingEngine
from app.ai.rag.chunker import TextChunker
from app.config import settings


class FAISSRetriever:
    """
    In-memory FAISS retriever for RAG.

    Workflow:
        1. index_document(text) → chunk → embed → add to FAISS index
        2. retrieve(query, k) → embed query → ANN search → return top-k chunks

    A separate instance is created per analysis request to keep state isolated.
    For a production system with many users, a persistent shared index would be used instead.
    """

    def __init__(self) -> None:
        self._engine = EmbeddingEngine.get_instance()
        self._chunker = TextChunker()
        self._dim = self._engine.dimension
        # Use flat inner product index (vectors are L2-normalized, so IP == cosine)
        self._index = faiss.IndexFlatIP(self._dim)
        self._chunks: List[str] = []  # Parallel list to FAISS index

    def index_document(self, text: str) -> int:
        """
        Chunk, embed, and add a document to the FAISS index.

        Args:
            text: Full document text (resume or JD).

        Returns:
            Number of chunks added.
        """
        chunks = self._chunker.chunk(text)
        if not chunks:
            return 0

        embeddings = self._engine.embed_batch(chunks)
        # FAISS expects float32
        embeddings = embeddings.astype(np.float32)
        self._index.add(embeddings)
        self._chunks.extend(chunks)
        logger.debug(f"Indexed {len(chunks)} chunks into FAISS")
        return len(chunks)

    def retrieve(self, query: str, k: int = None) -> List[str]:
        """
        Retrieve top-k most relevant chunks for a query.

        Args:
            query: Query text (e.g. the job description or a specific question).
            k: Number of chunks to retrieve.

        Returns:
            List of relevant text chunks, ordered by relevance.
        """
        k = k or settings.TOP_K_RESULTS
        if self._index.ntotal == 0:
            return []

        k = min(k, self._index.ntotal)
        query_vec = self._engine.embed(query).astype(np.float32).reshape(1, -1)
        distances, indices = self._index.search(query_vec, k)

        results: List[str] = []
        for idx in indices[0]:
            if idx >= 0 and idx < len(self._chunks):
                results.append(self._chunks[idx])

        return results

    def retrieve_with_scores(self, query: str, k: int = None) -> List[Tuple[str, float]]:
        """
        Retrieve top-k chunks with their cosine similarity scores.

        Returns:
            List of (chunk_text, score) tuples.
        """
        k = k or settings.TOP_K_RESULTS
        if self._index.ntotal == 0:
            return []

        k = min(k, self._index.ntotal)
        query_vec = self._engine.embed(query).astype(np.float32).reshape(1, -1)
        distances, indices = self._index.search(query_vec, k)

        results: List[Tuple[str, float]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self._chunks):
                results.append((self._chunks[idx], float(dist)))

        return results

    @property
    def total_chunks(self) -> int:
        return self._index.ntotal
