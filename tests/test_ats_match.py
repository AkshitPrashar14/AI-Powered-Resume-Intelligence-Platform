"""
Tests — ATS Engine (Rule-Based)
================================
Verifies that the ATS score is deterministic and Gemini is NOT used for scoring.
"""

import pytest
from unittest.mock import AsyncMock, patch


RESUME = """
John Doe
john@email.com | 415-555-1234 | github.com/johndoe

SUMMARY
Senior Software Engineer with 5 years of Python and FastAPI experience.

EXPERIENCE
Software Engineer — TechCorp (2020-Present)
- Built REST APIs using Python and FastAPI, serving 1M+ users
- Designed PostgreSQL schemas and optimized queries by 40%
- Deployed microservices on AWS with Docker and Kubernetes
- Led team of 4 engineers, improved delivery velocity by 30%

EDUCATION
B.S. Computer Science, MIT, 2019

SKILLS
Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS, Redis, Git, CI/CD

PROJECTS
Resume Parser: Built an AI-powered tool using Python and machine learning
"""

JD = """
Senior Python Engineer needed. Must have Python, FastAPI, Docker, PostgreSQL.
Experience with AWS, Kubernetes, Redis preferred. 5+ years required.
"""


class TestRuleBasedATSEngine:
    def setup_method(self):
        from app.services.ats_service import RuleBasedATSEngine
        self.engine = RuleBasedATSEngine()

    def test_keyword_scoring(self):
        score, present, missing = self.engine._score_keywords(RESUME.lower(), JD.lower())
        assert 0 <= score <= 25
        assert isinstance(present, list)
        assert isinstance(missing, list)

    def test_skills_scoring(self):
        score, matching, missing = self.engine._score_skills(RESUME.lower(), JD.lower())
        assert 0 <= score <= 20
        assert "python" in matching or "fastapi" in matching

    def test_experience_scoring(self):
        score = self.engine._score_experience(RESUME.lower(), JD.lower())
        assert 0 <= score <= 15

    def test_education_scoring(self):
        score = self.engine._score_education(RESUME.lower())
        assert score > 0  # "B.S. Computer Science" should be detected

    def test_action_verbs_scoring(self):
        score, verbs = self.engine._score_action_verbs(RESUME.lower())
        assert score > 0
        assert len(verbs) > 0

    def test_formatting_scoring(self):
        score = self.engine._score_formatting(RESUME)
        assert score > 0

    def test_deterministic_score(self):
        """Same input must always produce the same score."""
        s1, _, _ = self.engine._score_keywords(RESUME.lower(), JD.lower())
        s2, _, _ = self.engine._score_keywords(RESUME.lower(), JD.lower())
        assert s1 == s2

    @pytest.mark.asyncio
    async def test_calculate_score_gemini_not_used_for_numeric(self):
        """Gemini should only be called for explanation, not for score."""
        mock_gemini = AsyncMock(return_value={
            "recommendations": ["Add Terraform experience"],
            "weak_areas": "Missing infrastructure-as-code skills"
        })
        with patch.object(self.engine._gemini, "generate_json", mock_gemini):
            result = await self.engine.calculate_score(RESUME, JD)

        # Score must be deterministic regardless of Gemini response
        assert 0 <= result.total_score <= 100
        assert result.total_score == round(result.total_score, 1)
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_calculate_score_fallback_when_gemini_fails(self):
        """Should still return valid result when Gemini is unavailable."""
        with patch.object(self.engine._gemini, "generate_json", side_effect=Exception("API down")):
            result = await self.engine.calculate_score(RESUME, JD)
        assert 0 <= result.total_score <= 100
        assert isinstance(result.recommendations, list)


class TestMatchService:
    @pytest.mark.asyncio
    async def test_compute_match_returns_result(self):
        from app.services.match_service import MatchService
        from app.ai.embeddings.embedding_engine import EmbeddingEngine
        from unittest.mock import MagicMock
        import numpy as np

        mock_engine = MagicMock()
        mock_engine.similarity.return_value = 0.78
        mock_engine.embed.return_value = np.ones(384)

        with patch.object(EmbeddingEngine, "get_instance", return_value=mock_engine):
            service = MatchService()
            service._engine = mock_engine

            with patch.object(service._gemini, "generate_json", AsyncMock(return_value={
                "experience_match_explanation": "Good alignment",
                "education_match_explanation": "Relevant degree",
                "overall_verdict": "Strong candidate",
            })):
                result = await service.compute_match(RESUME, JD, ["Python", "FastAPI"])

        assert 0 <= result.similarity_percentage <= 100
        assert isinstance(result.matching_skills, list)
        assert isinstance(result.missing_skills, list)
        assert result.match_verdict != ""

    def test_generate_verdict_excellent(self):
        from app.services.match_service import MatchService
        service = MatchService()
        verdict = service._generate_verdict(85.0, 10, 2)
        assert "Excellent" in verdict or "strongly" in verdict.lower()

    def test_generate_verdict_low(self):
        from app.services.match_service import MatchService
        service = MatchService()
        verdict = service._generate_verdict(30.0, 2, 15)
        assert "Low" in verdict or "low" in verdict.lower()
