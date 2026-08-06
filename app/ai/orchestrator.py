"""
AI Orchestrator
===============
Central coordination layer for all AI workflows in the platform.

Every AI-related endpoint communicates through the AIOrchestrator
instead of calling individual services directly. This enforces:
    - Single entry point for all AI operations
    - Consistent logging and timing
    - Centralized cache management
    - Dependency lifecycle management (singleton reuse)
    - Clean separation between API layer and AI layer

Components coordinated:
    - FileParser          → text extraction from PDF/DOCX/TXT
    - EmbeddingEngine     → SentenceTransformer (singleton)
    - HybridEmbeddingCache → Redis L1 + Disk L2
    - FAISSRetriever      → vector search
    - RAGPipeline         → full retrieval-augmented generation
    - GeminiClient        → Google Gemini API
    - RuleBasedATSEngine  → deterministic ATS scoring
    - MatchService        → semantic resume-to-job matching
    - ImproveService      → STAR bullet rewriting
    - FeedbackService     → section-by-section feedback
    - SkillGapService     → learning roadmap generation
    - KeywordService      → ATS keyword optimization
    - ReportService       → PDF report generation
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.cache.embedding_cache import HybridEmbeddingCache
from app.ai.embeddings.embedding_engine import EmbeddingEngine
from app.ai.gemini_client import GeminiClient
from app.ai.rag.rag_pipeline import RAGPipeline
from app.ai.rag.retriever import FAISSRetriever
from app.database.repositories.analysis_repository import AnalysisRepository
from app.database.repositories.jd_repository import JobDescriptionRepository
from app.database.repositories.report_repository import ReportRepository
from app.database.repositories.resume_repository import ResumeRepository
from app.models.job_description import JobDescription
from app.schemas.schemas import FullAnalysisResult
from app.services.ats_service import RuleBasedATSEngine
from app.services.feedback_service import FeedbackService
from app.services.improve_service import ImproveService
from app.services.keyword_service import KeywordService
from app.services.match_service import MatchService
from app.services.skill_gap_service import SkillGapService
from app.utils.file_parser import FileParser


class AIOrchestrator:
    """
    Central coordinator for all AI workflows.

    Usage:
        orchestrator = AIOrchestrator(db)
        result = await orchestrator.run_full_analysis(resume_id, jd_text, user_id)

    All methods log timing, cache hits/misses, and component outputs.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

        # ── Repositories ─────────────────────────────────────────
        self._resume_repo = ResumeRepository(db)
        self._analysis_repo = AnalysisRepository(db)
        self._report_repo = ReportRepository(db)
        self._jd_repo = JobDescriptionRepository(db)

        # ── AI Components (singletons reused via class-level state) ──
        self._embedding_engine = EmbeddingEngine.get_instance()
        self._cache = HybridEmbeddingCache()
        self._parser = FileParser()

        # ── Stateless AI Services ─────────────────────────────────
        self._ats = RuleBasedATSEngine()
        self._match = MatchService()
        self._improve = ImproveService()
        self._feedback = FeedbackService()
        self._skill_gap = SkillGapService()
        self._keyword = KeywordService()

    async def run_full_analysis(
        self,
        resume_id: uuid.UUID,
        job_description_text: str,
        job_title: str = "",
        company: str = "",
    ) -> FullAnalysisResult:
        """
        Execute the complete AI analysis pipeline.

        Pipeline:
            1.  Load resume from PostgreSQL
            2.  Create/link JobDescription record
            3.  Create AnalysisHistory (status=RUNNING)
            4.  Parse resume for structured fields
            5.  Run AI services concurrently:
                a. Rule-based ATS scoring
                b. Semantic match (FAISS + SentenceTransformer)
                c. Skill gap detection (Gemini)
                d. Resume improvement (Gemini)
                e. Section feedback (Gemini)
                f. Keyword optimization (Gemini)
            6.  Run RAG full analysis (FAISS → Context → Gemini)
            7.  Persist results to analysis_history + reports
            8.  Return FullAnalysisResult

        Args:
            resume_id: UUID of the uploaded resume.
            job_description_text: Raw JD text.
            job_title: Optional job title for context.
            company: Optional company name.

        Returns:
            FullAnalysisResult with all AI results.
        """
        pipeline_start = time.perf_counter()
        logger.info(
            f"[ORCHESTRATOR] Starting full analysis — "
            f"resume={resume_id}"
        )

        # ── Step 1: Load resume ───────────────────────────────────────────────
        resume = await self._resume_repo.get_active(resume_id)
        if not resume:
            raise ValueError(f"Resume {resume_id} not found or not owned by user")

        resume_text = resume.parsed_text or ""
        if not resume_text.strip():
            raise ValueError("Resume has no parseable text content")

        logger.info(f"[ORCHESTRATOR] Resume loaded — {len(resume_text)} chars")

        # ── Step 2: Create/Link JobDescription record ─────────────────────────
        jd_record = await self._jd_repo.create(
            title=job_title or "Untitled Position",
            company=company or None,
            description=job_description_text,
        )
        logger.info(f"[ORCHESTRATOR] JD record created — id={jd_record.id}")

        # ── Step 3: Create AnalysisHistory (status=RUNNING) ───────────────────
        analysis = await self._analysis_repo.create(
            resume_id=resume_id,
            job_description_id=jd_record.id,
            status="running",
        )
        logger.info(f"[ORCHESTRATOR] Analysis started — id={analysis.id}")

        try:
            # ── Step 4: Parse resume for structured fields ────────────────────
            parsed = self._parser._extract_fields(resume_text)
            resume_skills = parsed.skills
            experience_bullets = parsed.experience
            logger.debug(f"[ORCHESTRATOR] Parsed {len(resume_skills)} skills, {len(experience_bullets)} bullets")

            # ── Step 5: Run AI services concurrently ──────────────────────────
            logger.info("[ORCHESTRATOR] Launching concurrent AI services...")
            t0 = time.perf_counter()

            (
                ats_result,
                match_result,
                skill_gap_result,
                improve_result,
                feedback_result,
                keyword_result,
            ) = await asyncio.gather(
                self._ats.calculate_score(resume_text, job_description_text),
                self._match.compute_match(resume_text, job_description_text, resume_skills),
                self._skill_gap.detect_gaps(resume_skills, job_description_text),
                self._improve.improve_resume(experience_bullets, job_description_text),
                self._feedback.get_feedback(resume_text, job_description_text),
                self._keyword.optimize_keywords(resume_text, job_description_text),
                return_exceptions=False,
            )

            services_elapsed = (time.perf_counter() - t0) * 1000
            logger.info(
                f"[ORCHESTRATOR] AI services complete — "
                f"ATS={ats_result.total_score:.1f}, "
                f"Match={match_result.similarity_percentage:.1f}%, "
                f"elapsed={services_elapsed:.0f}ms"
            )

            # ── Step 6: RAG full analysis ──────────────────────────────────────
            logger.info("[ORCHESTRATOR] Starting RAG pipeline...")
            rag = RAGPipeline()
            try:
                rag_data = await rag.run_full_analysis(resume_text, job_description_text)
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] RAG pipeline failed: {e}")
                rag_data = {}

            strengths = rag_data.get("strengths", [])
            weaknesses = rag_data.get("weaknesses", [])
            career_advice = rag_data.get("career_advice", "")
            interview_tips = rag_data.get("interview_tips", [])
            career_roadmap = rag_data.get("career_roadmap", [])
            recruiter_verdict = rag_data.get("recruiter_verdict", "")

            # ── Step 7: Build result ───────────────────────────────────────────
            result = FullAnalysisResult(
                analysis_id=analysis.id,
                ats_score=ats_result,
                match_result=match_result,
                skill_gap=skill_gap_result,
                improve_result=improve_result,
                feedback=feedback_result,
                keyword_result=keyword_result,
                strengths=strengths,
                weaknesses=weaknesses,
                career_advice=career_advice,
                interview_tips=interview_tips,
                career_roadmap=career_roadmap,
                recruiter_verdict=recruiter_verdict,
            )

            # ── Step 8: Persist to DB ──────────────────────────────────────────
            await self._analysis_repo.update(
                analysis.id,
                ats_score=ats_result.total_score,
                similarity_score=match_result.similarity_percentage,
                keyword_match_count=len(match_result.matching_skills),
                missing_skills_json=json.dumps(match_result.missing_skills),
                matched_skills_json=json.dumps(match_result.matching_skills),
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )

            # Build full report JSON
            report_json = {
                "ats_score": ats_result.model_dump(),
                "match_result": match_result.model_dump(),
                "skill_gap": skill_gap_result.model_dump(),
                "improve_result": improve_result.model_dump(),
                "feedback": feedback_result.model_dump(),
                "keyword_result": keyword_result.model_dump(),
                "strengths": strengths,
                "weaknesses": weaknesses,
                "career_advice": career_advice,
                "interview_tips": interview_tips,
                "career_roadmap": career_roadmap,
                "recruiter_verdict": recruiter_verdict,
            }

            await self._report_repo.create(
                analysis_id=analysis.id,
                strengths=json.dumps(strengths),
                weaknesses=json.dumps(weaknesses),
                recommendations=json.dumps(keyword_result.missing_ats_keywords),
                improved_resume=json.dumps(
                    [b.model_dump() for b in improve_result.improved_bullets]
                ),
                interview_tips=json.dumps(interview_tips),
                career_roadmap=json.dumps(career_roadmap),
                skill_gaps=json.dumps(
                    {
                        "high": skill_gap_result.high_priority_missing,
                        "medium": skill_gap_result.medium_priority_missing,
                        "future": skill_gap_result.future_skills,
                    }
                ),
                keyword_suggestions=json.dumps(keyword_result.missing_ats_keywords),
                section_feedback=json.dumps(
                    [s.model_dump() for s in feedback_result.sections]
                ),
                recruiter_verdict=recruiter_verdict,
                full_report_json=json.dumps(report_json),
            )

            total_elapsed = (time.perf_counter() - pipeline_start) * 1000
            logger.info(
                f"[ORCHESTRATOR] ✅ Analysis {analysis.id} complete — "
                f"total elapsed: {total_elapsed:.0f}ms"
            )

            return result

        except Exception as e:
            logger.error(
                f"[ORCHESTRATOR] ❌ Analysis {analysis.id} failed: {e}",
                exc_info=True,
            )
            await self._analysis_repo.update(
                analysis.id,
                status="failed",
                error_message=str(e),
            )
            raise

    async def run_ats_only(
        self, resume_id: uuid.UUID, job_description: str
    ):
        """Run only the ATS scoring pipeline."""
        resume = await self._resume_repo.get_active(resume_id)
        if not resume:
            raise ValueError(f"Resume {resume_id} not found")
        return await self._ats.calculate_score(resume.parsed_text or "", job_description)

    async def run_match_only(
        self,
        resume_id: uuid.UUID,
        job_description: str,
        resume_skills=None,
    ):
        """Run only the semantic matching pipeline."""
        resume = await self._resume_repo.get_active(resume_id)
        if not resume:
            raise ValueError(f"Resume {resume_id} not found")
        return await self._match.compute_match(
            resume.parsed_text or "", job_description, resume_skills or []
        )

    async def run_improve_only(
        self, resume_id: uuid.UUID, job_description: str
    ):
        """Run only the resume improvement pipeline."""
        resume = await self._resume_repo.get_active(resume_id)
        if not resume:
            raise ValueError(f"Resume {resume_id} not found")
        parsed = self._parser._extract_fields(resume.parsed_text or "")
        return await self._improve.improve_resume(parsed.experience, job_description)

    async def run_feedback_only(
        self, resume_id: uuid.UUID, job_description: str
    ):
        """Run only the section feedback pipeline."""
        resume = await self._resume_repo.get_active(resume_id)
        if not resume:
            raise ValueError(f"Resume {resume_id} not found")
        return await self._feedback.get_feedback(resume.parsed_text or "", job_description)
