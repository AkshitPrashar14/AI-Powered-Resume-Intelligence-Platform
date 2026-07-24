"""
Tests — Full Analysis Pipeline
================================
Tests for ATS service, file parser, and API endpoints.
Uses pytest-asyncio for async test support.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ats_service import ATSService
from app.utils.file_parser import FileParser


# ─────────────────────────────────────────────
# File Parser Tests
# ─────────────────────────────────────────────
class TestFileParser:
    """Unit tests for the FileParser utility."""

    def setup_method(self):
        self.parser = FileParser()

    def test_extract_email(self):
        text = "Contact me at john.doe@example.com for more info"
        result = self.parser._extract_email(text)
        assert result == "john.doe@example.com"

    def test_extract_email_none(self):
        result = self.parser._extract_email("No email here")
        assert result is None

    def test_extract_phone(self):
        text = "Call me at 415-555-1234 anytime"
        result = self.parser._extract_phone(text)
        assert result is not None
        assert "415" in result

    def test_extract_links(self):
        text = "github.com/johndoe and linkedin.com/in/johndoe"
        links = self.parser._extract_links(text)
        assert len(links) >= 1

    def test_extract_name_from_lines(self):
        lines = ["John Doe", "john@example.com", "415-555-1234"]
        name = self.parser._extract_name(lines)
        assert name == "John Doe"

    def test_extract_skills(self):
        lines = [
            "SKILLS",
            "Python, FastAPI, PostgreSQL, Docker, Kubernetes",
            "React, TypeScript, Node.js",
        ]
        # Manually test skills section extraction
        text = "\n".join(lines)
        all_lines = [l.strip() for l in text.split("\n") if l.strip()]
        skills = self.parser._extract_skills(all_lines)
        assert "Python" in skills or "python" in [s.lower() for s in skills]

    def test_parse_txt(self):
        txt_content = b"""John Smith
john.smith@email.com
415-555-9876

SUMMARY
Experienced software engineer with 5 years in backend development.

EXPERIENCE
Software Engineer at TechCorp
- Built REST APIs using Python and FastAPI
- Reduced response time by 40%

SKILLS
Python, FastAPI, PostgreSQL, Docker, AWS

EDUCATION
B.S. Computer Science, MIT, 2019
"""
        result = self.parser.parse(txt_content, "resume.txt")
        assert result.email == "john.smith@email.com"
        assert result.raw_text != ""
        assert len(result.skills) > 0

    def test_unsupported_extension(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            self.parser.parse(b"data", "file.xlsx")


# ─────────────────────────────────────────────
# ATS Service Tests
# ─────────────────────────────────────────────
class TestATSService:
    """Unit tests for the ATS scoring service."""

    def setup_method(self):
        self.service = ATSService()

    def test_fallback_score_basic(self):
        resume = """
        John Doe
        john@example.com
        
        EXPERIENCE
        Software Engineer at TechCorp
        Built Python APIs and managed PostgreSQL databases
        Improved performance by 30%
        
        EDUCATION
        B.S. Computer Science
        
        SKILLS
        Python, FastAPI, Docker, PostgreSQL
        """
        jd = """
        We need a Software Engineer with Python, FastAPI, Docker, and SQL experience.
        The ideal candidate has experience with microservices and cloud platforms.
        """
        result = self.service._fallback_score(resume, jd)
        assert 0 <= result.total_score <= 100
        assert isinstance(result.missing_keywords, list)
        assert isinstance(result.present_keywords, list)
        assert isinstance(result.recommendations, list)

    def test_fallback_score_empty_resume(self):
        result = self.service._fallback_score("", "Python developer needed")
        assert result.total_score >= 0

    @pytest.mark.asyncio
    async def test_calculate_score_with_mocked_gemini(self):
        mock_response = {
            "total_score": 72.5,
            "keyword_score": 15.0,
            "format_score": 12.0,
            "skills_score": 16.0,
            "experience_score": 13.0,
            "education_score": 8.0,
            "sections_score": 5.0,
            "action_verbs_score": 3.5,
            "missing_keywords": ["kubernetes", "terraform"],
            "present_keywords": ["python", "fastapi", "docker"],
            "recommendations": ["Add more cloud experience"],
            "breakdown": {"summary": "Good resume, needs cloud skills"},
        }

        with patch.object(
            self.service._gemini,
            "generate_json",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await self.service.calculate_score(
                resume_text="Python developer with FastAPI experience",
                job_description="Looking for Python FastAPI developer",
            )
            assert result.total_score == 72.5
            assert "kubernetes" in result.missing_keywords
            assert "python" in result.present_keywords


# ─────────────────────────────────────────────
# Match Service Tests
# ─────────────────────────────────────────────
class TestMatchService:
    """Unit tests for the semantic match service."""

    @pytest.mark.asyncio
    async def test_compute_match_returns_result(self):
        from app.services.match_service import MatchService
        from app.ai.embeddings.embedding_engine import EmbeddingEngine

        with patch.object(EmbeddingEngine, "get_instance") as mock_engine:
            mock_instance = MagicMock()
            mock_instance.similarity.return_value = 0.75
            mock_engine.return_value = mock_instance

            service = MatchService()
            service._engine = mock_instance

            result = await service.compute_match(
                resume_text="Python developer with FastAPI, Docker, PostgreSQL experience",
                job_description="Looking for Python FastAPI developer with Docker knowledge",
                resume_skills=["Python", "FastAPI", "Docker"],
            )
            assert 0 <= result.similarity_percentage <= 100
            assert isinstance(result.matching_skills, list)
            assert isinstance(result.missing_skills, list)

    def test_generate_verdict_excellent(self):
        from app.services.match_service import MatchService
        service = MatchService()
        verdict = service._generate_verdict(85.0, 10, 2)
        assert "Excellent" in verdict

    def test_generate_verdict_low(self):
        from app.services.match_service import MatchService
        service = MatchService()
        verdict = service._generate_verdict(30.0, 2, 15)
        assert "Low" in verdict


# ─────────────────────────────────────────────
# TextChunker Tests
# ─────────────────────────────────────────────
class TestTextChunker:
    def setup_method(self):
        from app.ai.rag.chunker import TextChunker
        self.chunker = TextChunker(chunk_size=200, overlap=30)

    def test_empty_text(self):
        result = self.chunker.chunk("")
        assert result == []

    def test_short_text_single_chunk(self):
        text = "This is a short resume with minimal content."
        chunks = self.chunker.chunk(text)
        assert len(chunks) >= 1
        assert "resume" in chunks[0]

    def test_long_text_multiple_chunks(self):
        # Create text longer than chunk_size
        long_text = ("This is a paragraph about software engineering. " * 10 + "\n\n") * 5
        chunks = self.chunker.chunk(long_text)
        assert len(chunks) > 1

    def test_no_empty_chunks(self):
        text = "\n\n".join(["Paragraph " + str(i) for i in range(20)])
        chunks = self.chunker.chunk(text)
        for chunk in chunks:
            assert chunk.strip() != ""


# ─────────────────────────────────────────────
# EmbeddingCache Tests
# ─────────────────────────────────────────────
class TestEmbeddingCache:
    def setup_method(self):
        import tempfile
        import os
        from app.ai.cache.embedding_cache import EmbeddingCache

        # Use a temp dir to avoid polluting real cache
        self.temp_dir = tempfile.mkdtemp()
        with patch("app.ai.cache.embedding_cache.settings") as mock_settings:
            mock_settings.EMBEDDING_CACHE_DIR = self.temp_dir
            self.cache = EmbeddingCache()
            self.cache.cache_dir = self.temp_dir

    def test_cache_miss_returns_none(self):
        result = self.cache.get("text that was never cached")
        assert result is None

    def test_cache_set_and_get(self):
        import numpy as np
        text = "Test embedding text for cache"
        embedding = np.array([0.1, 0.2, 0.3, 0.4])
        self.cache.set(text, embedding)
        retrieved = self.cache.get(text)
        assert retrieved is not None
        assert np.allclose(retrieved, embedding)

    def test_cache_invalidate(self):
        import numpy as np
        text = "Text to invalidate"
        self.cache.set(text, np.zeros(10))
        removed = self.cache.invalidate(text)
        assert removed is True
        assert self.cache.get(text) is None

    def test_cache_size(self):
        import numpy as np
        initial_size = self.cache.size()
        self.cache.set("unique_text_123", np.zeros(5))
        assert self.cache.size() == initial_size + 1
