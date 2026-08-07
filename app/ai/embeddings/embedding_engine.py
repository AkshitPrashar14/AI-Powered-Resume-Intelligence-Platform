"""
Embedding Engine
================
Singleton wrapper around Gemini Embeddings API for generating
dense vector embeddings. Integrates with HybridEmbeddingCache to avoid
redundant inference on repeated texts.

Performance:
    - Thread-safe singleton via double-checked locking
    - Batch inference for multiple texts
    - L1 Redis + L2 Disk cache lookup before every encode() call
    - Normalized vectors (L2) → cosine sim = dot product
"""

import threading
import time
from typing import List, Optional

import numpy as np
from loguru import logger
import google.generativeai as genai

from app.ai.cache.embedding_cache import HybridEmbeddingCache
from app.config import settings


class EmbeddingEngine:
    """
    Thread-safe singleton for sentence embedding inference via Gemini API.

    Uses Gemini text-embedding-004 and wraps
    it with a HybridEmbeddingCache so repeated texts don't cause API calls.

    Usage:
        engine = EmbeddingEngine.get_instance()
        vector = engine.embed("some text")
        vectors = engine.embed_batch(["text1", "text2"])
    """

    _instance: Optional["EmbeddingEngine"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        logger.info("[EMBED] Initializing Gemini Embeddings API (text-embedding-004)")
        t0 = time.perf_counter()
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model_name = "models/gemini-embedding-001"
        self._cache = HybridEmbeddingCache()
        self._dim = 3072  # Gemini embedding dimension
        
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(
            f"[EMBED] ✅ Model ready — dim={self._dim}, "
            f"load_time={elapsed:.0f}ms, model={self._model_name}"
        )

    @classmethod
    def get_instance(cls) -> "EmbeddingEngine":
        """
        Return the singleton instance, initializing it if needed.
        Thread-safe via double-checked locking.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def dimension(self) -> int:
        """Return embedding vector dimension."""
        return self._dim

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """L2-normalize a vector."""
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm

    def embed(self, text: str) -> np.ndarray:
        """
        Embed a single text string.

        Checks hybrid cache first (Redis → Disk); calls Gemini API only on a
        cache miss.

        Args:
            text: Input text to embed.

        Returns:
            numpy array of shape (embedding_dim,), L2-normalized.
        """
        text = text.strip()

        # Cache lookup
        cached = self._cache.get_embedding(text)
        if cached is not None:
            return cached

        # Inference
        t0 = time.perf_counter()
        result = genai.embed_content(
            model=self._model_name,
            content=text,
            task_type="retrieval_document"
        )
        embedding = np.array(result['embedding'], dtype=np.float32)
        embedding = self._normalize(embedding)
        
        elapsed = (time.perf_counter() - t0) * 1000
        logger.debug(f"[EMBED] Inference {elapsed:.1f}ms — {len(text)} chars")

        self._cache.set_embedding(text, embedding)
        return embedding

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Embed multiple texts efficiently.

        Cache-hits are returned immediately; remaining texts are batched
        into a single Gemini API inference call.

        Args:
            texts: List of input strings.

        Returns:
            numpy array of shape (len(texts), embedding_dim).
        """
        results: List[Optional[np.ndarray]] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        for i, text in enumerate(texts):
            cached = self._cache.get_embedding(text.strip())
            if cached is not None:
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(text.strip())

        if uncached_texts:
            t0 = time.perf_counter()
            # Batch inference
            batch_result = genai.embed_content(
                model=self._model_name,
                content=uncached_texts,
                task_type="retrieval_document"
            )
            elapsed = (time.perf_counter() - t0) * 1000
            logger.debug(
                f"[EMBED] Batch inference — {len(uncached_texts)} texts "
                f"in {elapsed:.1f}ms"
            )
            
            embeddings_list = batch_result['embedding']
            for idx, (orig_idx, text) in enumerate(zip(uncached_indices, uncached_texts)):
                emb = np.array(embeddings_list[idx], dtype=np.float32)
                emb = self._normalize(emb)
                self._cache.set_embedding(text, emb)
                results[orig_idx] = emb

        return np.vstack(results)

    def similarity(self, text_a: str, text_b: str) -> float:
        """
        Compute cosine similarity between two texts.

        Checks similarity cache first to avoid recomputation.

        Returns:
            Float in range [0, 1].
        """
        # Check similarity cache
        cached_sim = self._cache.get_similarity(text_a, text_b)
        if cached_sim is not None:
            logger.debug("[EMBED] Similarity cache HIT")
            return cached_sim

        vec_a = self.embed(text_a)
        vec_b = self.embed(text_b)
        # Both vectors are L2-normalized, so dot product = cosine sim
        score = float(np.dot(vec_a, vec_b))
        score = max(0.0, min(1.0, score))

        # Cache result
        self._cache.set_similarity(text_a, text_b, score)
        return score
