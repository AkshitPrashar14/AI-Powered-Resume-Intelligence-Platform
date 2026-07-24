"""
Tests — Hybrid Embedding Cache
================================
Tests for Redis L1 + Disk L2 cache, including fallback behavior.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class TestHybridEmbeddingCache:
    def setup_method(self):
        from app.ai.cache.embedding_cache import HybridEmbeddingCache
        self.temp_dir = tempfile.mkdtemp()
        with patch("app.ai.cache.embedding_cache.settings") as ms:
            ms.EMBEDDING_CACHE_DIR = self.temp_dir
            ms.REDIS_URL = "redis://localhost:6379/0"
            self.cache = HybridEmbeddingCache()
            self.cache.cache_dir = self.temp_dir

    def test_cache_miss_returns_none(self):
        result = self.cache.get_embedding("text that was never cached")
        assert result is None

    def test_disk_set_and_get(self):
        text = "test embedding text"
        emb = np.array([0.1, 0.2, 0.3])
        self.cache.set_embedding(text, emb)
        retrieved = self.cache.get_embedding(text)
        assert retrieved is not None
        assert np.allclose(retrieved, emb)

    def test_sha256_key_is_deterministic(self):
        key1 = self.cache._sha256("hello world")
        key2 = self.cache._sha256("hello world")
        assert key1 == key2

    def test_sha256_different_inputs_different_keys(self):
        k1 = self.cache._sha256("text A")
        k2 = self.cache._sha256("text B")
        assert k1 != k2

    def test_composite_key(self):
        k1 = self.cache._composite_key("resume text", "jd text")
        k2 = self.cache._composite_key("resume text", "jd text")
        k3 = self.cache._composite_key("other resume", "jd text")
        assert k1 == k2
        assert k1 != k3

    def test_disk_size_increments(self):
        size_before = self.cache.disk_size()
        self.cache.set_embedding("unique-text-xyz-123", np.zeros(5))
        assert self.cache.disk_size() == size_before + 1

    def test_invalidate_removes_from_disk(self):
        text = "text to invalidate"
        self.cache.set_embedding(text, np.zeros(10))
        removed = self.cache.invalidate_embedding(text)
        assert removed is True
        assert self.cache.get_embedding(text) is None

    def test_response_cache_set_get(self):
        key = "test-response-key-abc"
        data = {"strengths": ["Python", "FastAPI"], "score": 85}
        self.cache.set_response(key, data)
        retrieved = self.cache.get_response(key)
        assert retrieved is not None
        assert retrieved.get("score") == 85

    def test_redis_fallback_when_unavailable(self):
        """Cache should work on disk-only when Redis is unreachable."""
        with patch("app.ai.cache.embedding_cache._get_redis", return_value=None):
            text = "fallback test"
            emb = np.array([1.0, 2.0])
            self.cache.set_embedding(text, emb)
            result = self.cache.get_embedding(text)
            assert result is not None
            assert np.allclose(result, emb)
