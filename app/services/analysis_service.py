"""
Analysis Orchestrator Service
==============================
Thin wrapper over AIOrchestrator — delegates all logic to the orchestrator.
Kept for backward compatibility with existing router imports.
"""

import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestrator import AIOrchestrator
from app.schemas.schemas import FullAnalysisResult


class AnalysisService:
    """
    Delegates all analysis logic to AIOrchestrator.

    Args:
        db: Injected async database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._orchestrator = AIOrchestrator(db)

    async def run_analysis(
        self,
        resume_id: uuid.UUID,
        job_description: str,
        user_id: uuid.UUID,
        job_title: str = "",
        company: str = "",
    ) -> FullAnalysisResult:
        """
        Execute the full analysis pipeline via AIOrchestrator.

        Args:
            resume_id: UUID of the previously uploaded resume.
            job_description: Raw job description text.
            user_id: Authenticated user UUID.
            job_title: Optional job title for context.
            company: Optional company name.

        Returns:
            FullAnalysisResult with all AI analysis results.
        """
        return await self._orchestrator.run_full_analysis(
            resume_id=resume_id,
            job_description_text=job_description,
            user_id=user_id,
            job_title=job_title or "",
            company=company or "",
        )
