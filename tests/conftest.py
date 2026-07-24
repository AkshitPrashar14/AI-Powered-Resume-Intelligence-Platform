"""
Tests — Conftest
=================
Shared pytest fixtures.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock

# Set test environment variables before any imports
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/resume_test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql+psycopg2://postgres:password@localhost:5432/resume_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("GEMINI_API_KEY", "fake-api-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture
def mock_gemini():
    """Mock GeminiClient that returns a predefined response."""
    mock = MagicMock()
    mock.generate_json = AsyncMock(return_value={
        "strengths": ["Strong Python skills", "Good experience"],
        "weaknesses": ["Missing Kubernetes certification"],
        "career_advice": "Focus on cloud-native technologies",
        "interview_tips": ["Prepare system design questions"],
        "career_roadmap": ["Get AWS certified", "Learn Kubernetes"],
        "recruiter_verdict": "Strong candidate",
        "certification_recommendations": ["AWS SAA"],
        "project_recommendations": ["Build a distributed system"],
    })
    mock.generate_json_list = AsyncMock(return_value=[
        {"original": "Built APIs", "improved": "Architected REST APIs serving 1M users", "explanation": "Added scale"}
    ])
    return mock


@pytest.fixture
def mock_embedding_engine():
    """Mock EmbeddingEngine that returns a fixed vector."""
    import numpy as np
    mock = MagicMock()
    mock.embed.return_value = np.random.rand(384).astype("float32")
    mock.embed_batch.return_value = np.random.rand(5, 384).astype("float32")
    mock.similarity.return_value = 0.75
    mock.dimension = 384
    return mock


@pytest.fixture
def sample_resume_text():
    return """
John Doe
john@email.com | 415-555-1234

SUMMARY
Software Engineer with 4 years experience in Python and FastAPI.

EXPERIENCE
Backend Engineer at TechCorp (2021-Present)
- Built microservices using Python, FastAPI, and PostgreSQL
- Deployed applications on AWS using Docker and Kubernetes
- Improved query performance by 40% through indexing

EDUCATION
B.S. Computer Science, Stanford University, 2020

SKILLS
Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS, Redis, Git

PROJECTS
AI Resume Parser — Python, FastAPI, FAISS, Sentence Transformers
"""


@pytest.fixture
def sample_jd_text():
    return """
Senior Python Engineer
We need a Senior Python Engineer with 3+ years of experience.
Required: Python, FastAPI, PostgreSQL, Docker, AWS.
Nice to have: Kubernetes, Redis, ML experience.
"""
