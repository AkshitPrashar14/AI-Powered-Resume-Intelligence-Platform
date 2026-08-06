"""
Hybrid Embedding Cache
======================
Two-tier caching for sentence transformer embeddings and AI responses.

Architecture:
    L1 = Redis  (fast, TTL-based, shared across workers)
    L2 = Disk   (persistent fallback, pickle files)

Cache Key: SHA-256(text) — collision-resistant, deterministic.

Gracefully degrades to disk-only if Redis is unavailable.
"""

import hashlib
import json
import os
import pickle
import time
from typing import Any, Optional

import numpy as np
from loguru import logger

from app.config import settings


# ── Redis client (optional) ──────────────────────────────────────────────────
_redis_client: Optional[Any] = None
_redis_available: bool = False


def _get_redis():
    """Return the Redis client, initializing it on first call."""
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client if _redis_available else None

    try:
        import redis
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=False,
        )
        client.ping()
        _redis_client = client
        _redis_available = True
        logger.info(f"✅ Redis connected: {settings.REDIS_URL}")
    except Exception as e:
        _redis_available = False
        _redis_client = None
        logger.warning(f"⚠️  Redis unavailable — falling back to disk cache only. ({e})")

    return _redis_client if _redis_available else None


class HybridEmbeddingCache:
    """
    Two-tier embedding cache: Redis (L1) → Disk (L2).

    Usage:
        cache = HybridEmbeddingCache()
        vec = cache.get_embedding("some text")
        if vec is None:
            vec = model.encode("some text")
            cache.set_embedding("some text", vec)
    """

    # TTL for Redis keys (24 hours by default)
    EMBEDDING_TTL: int = 86_400
    RESPONSE_TTL: int = 43_200  # 12 hours for Gemini responses

    def __init__(self) -> None:
        self.cache_dir = settings.EMBEDDING_CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.debug(f"HybridEmbeddingCache ready — disk dir: {self.cache_dir}")

    # ── Key Generation ────────────────────────────────────────────────────────
    @staticmethod
    def _sha256(text: str) -> str:
        """Generate a SHA-256 hash of the input text (used as cache key)."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _composite_key(text_a: str, text_b: str) -> str:
        """Composite key for pairwise lookups (resume + JD)."""
        combined = text_a.strip() + "|||" + text_b.strip()
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _disk_path(self, key: str, suffix: str = "emb") -> str:
        return os.path.join(self.cache_dir, f"{key}.{suffix}.pkl")

    # ── Embedding Cache ───────────────────────────────────────────────────────
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Retrieve a cached embedding vector.

        Checks Redis (L1) first, falls back to disk (L2).

        Args:
            text: The source text whose embedding we want.

        Returns:
            numpy array if cached, None on cache miss.
        """
        key = self._sha256(text.strip())
        redis_key = f"emb:{key}"

        # L1: Redis
        r = _get_redis()
        if r:
            try:
                t0 = time.perf_counter()
                raw = r.get(redis_key)
                if raw is not None:
                    embedding = pickle.loads(raw)
                    elapsed = (time.perf_counter() - t0) * 1000
                    logger.debug(f"[CACHE] Redis HIT  key={key[:8]}… ({elapsed:.1f}ms)")
                    return embedding
            except Exception as e:
                logger.warning(f"[CACHE] Redis GET error: {e}")

        # L2: Disk
        disk_path = self._disk_path(key)
        if os.path.exists(disk_path):
            try:
                t0 = time.perf_counter()
                with open(disk_path, "rb") as f:
                    embedding = pickle.load(f)
                elapsed = (time.perf_counter() - t0) * 1000
                logger.debug(f"[CACHE] Disk  HIT  key={key[:8]}… ({elapsed:.1f}ms)")
                # Promote to Redis
                if r:
                    try:
                        r.setex(redis_key, self.EMBEDDING_TTL, pickle.dumps(embedding))
                    except Exception:
                        pass
                return embedding
            except Exception as e:
                logger.warning(f"[CACHE] Disk read error: {e}")

        logger.debug(f"[CACHE] MISS key={key[:8]}…")
        return None

    def set_embedding(self, text: str, embedding: np.ndarray) -> None:
        """
        Persist an embedding to both Redis (L1) and disk (L2).

        Args:
            text: The source text.
            embedding: The resulting numpy array.
        """
        key = self._sha256(text.strip())
        serialized = pickle.dumps(embedding, protocol=pickle.HIGHEST_PROTOCOL)

        # L1: Redis
        r = _get_redis()
        if r:
            try:
                r.setex(f"emb:{key}", self.EMBEDDING_TTL, serialized)
                logger.debug(f"[CACHE] Redis SET key={key[:8]}…")
            except Exception as e:
                logger.warning(f"[CACHE] Redis SET error: {e}")

        # L2: Disk
        try:
            with open(self._disk_path(key), "wb") as f:
                f.write(serialized)
            logger.debug(f"[CACHE] Disk  SET key={key[:8]}…")
        except Exception as e:
            logger.warning(f"[CACHE] Disk write error: {e}")

    # ── Generic JSON Response Cache ───────────────────────────────────────────
    def get_response(self, cache_key: str) -> Optional[dict]:
        """
        Retrieve a cached Gemini JSON response.

        Args:
            cache_key: SHA-256 composite key (resume_text + jd_text).

        Returns:
            Parsed dict if cached, None otherwise.
        """
        redis_key = f"resp:{cache_key}"

        # L1: Redis
        r = _get_redis()
        if r:
            try:
                raw = r.get(redis_key)
                if raw is not None:
                    logger.debug(f"[CACHE] Redis HIT  resp={cache_key[:8]}…")
                    return json.loads(raw)
            except Exception as e:
                logger.warning(f"[CACHE] Redis GET resp error: {e}")

        # L2: Disk
        disk_path = self._disk_path(cache_key, "resp")
        if os.path.exists(disk_path):
            try:
                with open(disk_path, "rb") as f:
                    data = pickle.load(f)
                logger.debug(f"[CACHE] Disk  HIT  resp={cache_key[:8]}…")
                return data
            except Exception as e:
                logger.warning(f"[CACHE] Disk read resp error: {e}")

        return None

    def set_response(self, cache_key: str, response: dict) -> None:
        """Cache a Gemini JSON response."""
        redis_key = f"resp:{cache_key}"
        serialized_json = json.dumps(response)
        serialized_pkl = pickle.dumps(response, protocol=pickle.HIGHEST_PROTOCOL)

        r = _get_redis()
        if r:
            try:
                r.setex(redis_key, self.RESPONSE_TTL, serialized_json.encode())
                logger.debug(f"[CACHE] Redis SET resp={cache_key[:8]}…")
            except Exception as e:
                logger.warning(f"[CACHE] Redis SET resp error: {e}")

        try:
            with open(self._disk_path(cache_key, "resp"), "wb") as f:
                f.write(serialized_pkl)
        except Exception as e:
            logger.warning(f"[CACHE] Disk write resp error: {e}")

    # ── Similarity Cache ──────────────────────────────────────────────────────
    def get_similarity(self, resume_text: str, jd_text: str) -> Optional[float]:
        """Return cached cosine similarity score for a resume+JD pair."""
        key = self._composite_key(resume_text, jd_text)
        r = _get_redis()
        if r:
            try:
                val = r.get(f"sim:{key}")
                if val is not None:
                    logger.debug(f"[CACHE] Redis HIT  sim={key[:8]}…")
                    return float(val)
            except Exception:
                pass
        return None

    def set_similarity(self, resume_text: str, jd_text: str, score: float) -> None:
        """Cache cosine similarity score."""
        key = self._composite_key(resume_text, jd_text)
        r = _get_redis()
        if r:
            try:
                r.setex(f"sim:{key}", self.RESPONSE_TTL, str(score).encode())
            except Exception:
                pass

    # ── Utilities ─────────────────────────────────────────────────────────────
    def invalidate_embedding(self, text: str) -> bool:
        """Remove a specific embedding from both tiers."""
        key = self._sha256(text.strip())
        removed = False

        r = _get_redis()
        if r:
            try:
                r.delete(f"emb:{key}")
                removed = True
            except Exception:
                pass

        disk_path = self._disk_path(key)
        if os.path.exists(disk_path):
            os.remove(disk_path)
            removed = True

        return removed

    def disk_size(self) -> int:
        """Return number of cached files on disk."""
        return len([f for f in os.listdir(self.cache_dir) if f.endswith(".pkl")])

    def redis_available(self) -> bool:
        """Return True if Redis is connected."""
        return _redis_available


# ── Legacy alias for backwards compatibility ──────────────────────────────────
EmbeddingCache = HybridEmbeddingCache
