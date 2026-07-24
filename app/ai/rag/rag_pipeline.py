"""
RAG Pipeline
=============
Full Retrieval-Augmented Generation pipeline with every stage explicit
and independently reusable:

  Resume Text
    ↓ TextChunker.chunk()
    ↓ EmbeddingEngine.embed_batch()   ← Sentence Transformers (all-MiniLM-L6-v2)
    ↓ HybridCache.check()             ← Redis L1 / Disk L2
    ↓ FAISSRetriever.index_document() ← FAISS IndexFlatIP
    ↓ FAISSRetriever.retrieve(k=5)    ← Top-K semantic search
    ↓ ContextBuilder.build(chunks)    ← Format retrieved chunks
    ↓ PromptTemplates.full_analysis() ← Prompt assembly
    ↓ GeminiClient.generate_json()    ← Gemini API call
    ↓ Structured JSON Response

This is genuine RAG — chunks are retrieved from FAISS BEFORE calling Gemini.
The retrieved context is injected into the Gemini prompt.
"""

import hashlib
import time
from typing import Any, Dict, List, Optional

from loguru import logger

from app.ai.cache.embedding_cache import HybridEmbeddingCache
from app.ai.gemini_client import GeminiClient
from app.ai.rag.retriever import FAISSRetriever
from app.prompts.templates import PromptTemplates


class ContextBuilder:
    """
    Formats retrieved FAISS chunks into a coherent context string
    for injection into the Gemini prompt.
    """

    @staticmethod
    def build(chunks: List[str], max_chars: int = 3000) -> str:
        """
        Join retrieved chunks into a formatted context block.

        Args:
            chunks: Top-k text chunks from FAISS retrieval.
            max_chars: Maximum total characters in the context.

        Returns:
            Formatted context string.
        """
        if not chunks:
            return "No additional context retrieved."

        sections = []
        total_chars = 0
        for i, chunk in enumerate(chunks, 1):
            chunk_text = chunk.strip()
            if total_chars + len(chunk_text) > max_chars:
                break
            sections.append(f"[Chunk {i}]\n{chunk_text}")
            total_chars += len(chunk_text)

        return "\n\n---\n\n".join(sections)


class RAGPipeline:
    """
    Orchestrates the full RAG pipeline for resume intelligence analysis.

    A new instance is created per analysis request (state isolation).
    The EmbeddingEngine singleton is reused across all instances.

    Usage:
        pipeline = RAGPipeline()
        result = await pipeline.run_full_analysis(resume_text, jd_text)
    """

    def __init__(self) -> None:
        self._retriever = FAISSRetriever()
        self._gemini = GeminiClient()
        self._cache = HybridEmbeddingCache()
        self._context_builder = ContextBuilder()
        self._indexed = False

    # ── Stage 1 & 2: Chunk → Embed → Index ───────────────────────────────────
    async def index(self, resume_text: str, jd_text: str) -> None:
        """
        Stage 1 (Chunking) + Stage 2 (Embedding) + Stage 3 (FAISS Indexing).

        Chunks both documents, embeds each chunk using SentenceTransformer,
        and loads them into the FAISS in-memory index.

        Args:
            resume_text: Full parsed resume text.
            jd_text: Full job description text.
        """
        t0 = time.perf_counter()
        logger.info("[RAG] Stage 1-3: Chunking → Embedding → FAISS indexing...")

        resume_chunks = self._retriever.index_document(resume_text)
        jd_chunks = self._retriever.index_document(jd_text)

        elapsed = (time.perf_counter() - t0) * 1000
        self._indexed = True
        logger.info(
            f"[RAG] Indexed {resume_chunks} resume chunks + {jd_chunks} JD chunks "
            f"in {elapsed:.0f}ms — total FAISS vectors: {self._retriever.total_chunks}"
        )

    # ── Stage 4: Cache Lookup ─────────────────────────────────────────────────
    def _check_response_cache(self, resume_text: str, jd_text: str) -> Optional[Dict]:
        """
        Stage 4: Check Redis/disk cache for an existing Gemini response.

        Returns:
            Cached response dict if available, None otherwise.
        """
        cache_key = hashlib.sha256(
            (resume_text[:3000] + jd_text[:2000]).encode()
        ).hexdigest()
        cached = self._cache.get_response(f"rag:{cache_key}")
        if cached:
            logger.info(f"[RAG] Stage 4: Cache HIT — key={cache_key[:8]}…")
        else:
            logger.debug(f"[RAG] Stage 4: Cache MISS — key={cache_key[:8]}…")
        return cached, cache_key

    # ── Stage 5: Retrieve ─────────────────────────────────────────────────────
    def retrieve_context(self, query: str, k: int = 5) -> str:
        """
        Stage 5: FAISS Top-K Retrieval → Context Builder.

        Searches the FAISS index for the top-k chunks most semantically
        similar to the query, then formats them into a context string.

        Args:
            query: Semantic query (e.g. skills required for the role).
            k: Number of chunks to retrieve.

        Returns:
            Formatted context string for the Gemini prompt.
        """
        if not self._indexed:
            return "No context available — index not initialized."

        t0 = time.perf_counter()
        chunks = self._retriever.retrieve(query, k=k)
        elapsed = (time.perf_counter() - t0) * 1000

        logger.info(
            f"[RAG] Stage 5: FAISS retrieved {len(chunks)} chunks "
            f"in {elapsed:.1f}ms"
        )

        context = self._context_builder.build(chunks)
        return context

    # ── Stage 6-8: Prompt → Gemini → Response ────────────────────────────────
    async def run_full_analysis(
        self, resume_text: str, jd_text: str
    ) -> Dict[str, Any]:
        """
        Full RAG pipeline — returns structured Gemini output.

        Stages:
            1. Chunk documents (TextChunker)
            2. Embed chunks (SentenceTransformer)
            3. Build FAISS index
            4. Check cache (Redis L1 → Disk L2)
            5. Retrieve top-k chunks (FAISS)
            6. Build context (ContextBuilder)
            7. Assemble prompt (PromptTemplates)
            8. Call Gemini (GeminiClient)
            Return: Structured JSON

        Args:
            resume_text: Parsed resume text.
            jd_text: Job description text.

        Returns:
            Parsed JSON dict with strengths, weaknesses, advice, etc.
        """
        logger.info("[RAG] Starting full RAG pipeline...")

        # Stage 4: Cache check FIRST to avoid redundant work
        cached_response, cache_key = self._check_response_cache(resume_text, jd_text)
        if cached_response:
            return cached_response

        # Stages 1-3: Index if not already done
        if not self._indexed:
            await self.index(resume_text, jd_text)

        # Stage 5: Retrieve top-k chunks relevant to job requirements
        query = f"skills qualifications requirements experience: {jd_text[:300]}"
        context = self.retrieve_context(query, k=5)

        # Stage 6: Build prompt with retrieved context
        logger.info("[RAG] Stage 6: Assembling prompt with retrieved context...")
        prompt = PromptTemplates.full_analysis(resume_text, jd_text, context)

        # Stage 7-8: Call Gemini
        t0 = time.perf_counter()
        logger.info("[RAG] Stage 7: Calling Gemini...")
        result = await self._gemini.generate_json(prompt)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(f"[RAG] Stage 8: Gemini response received in {elapsed:.0f}ms")

        # Cache the response
        self._cache.set_response(f"rag:{cache_key}", result)

        return result

    # ── Utility: Compute semantic similarity ──────────────────────────────────
    def compute_semantic_similarity(self, resume_text: str, jd_text: str) -> float:
        """
        Compute cosine similarity between resume and JD embeddings.

        Returns:
            Float in [0, 1] representing semantic overlap.
        """
        from app.ai.embeddings.embedding_engine import EmbeddingEngine
        engine = EmbeddingEngine.get_instance()
        return engine.similarity(resume_text[:2000], jd_text[:2000])
