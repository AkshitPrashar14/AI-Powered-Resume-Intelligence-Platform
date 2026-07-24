"""
Skill Gap Detection Service
============================
Compares resume skills vs JD requirements and generates a learning roadmap.
"""

from typing import List

from loguru import logger

from app.ai.gemini_client import GeminiClient
from app.prompts.templates import PromptTemplates
from app.schemas.schemas import SkillGapResult


class SkillGapService:
    """
    Detects missing skills and generates a prioritized learning roadmap.
    Uses Gemini for intelligent gap analysis with priority classification.
    """

    def __init__(self) -> None:
        self._gemini = GeminiClient()

    async def detect_gaps(
        self, resume_skills: List[str], job_description: str
    ) -> SkillGapResult:
        """
        Identify skill gaps between resume and job description.

        Args:
            resume_skills: Skills extracted from the resume.
            job_description: Target job description text.

        Returns:
            SkillGapResult with prioritized gaps and learning roadmap.
        """
        logger.info(f"Detecting skill gaps for {len(resume_skills)} resume skills...")

        try:
            prompt = PromptTemplates.skill_gap(resume_skills, job_description)
            data = await self._gemini.generate_json(prompt)

            return SkillGapResult(
                resume_skills=resume_skills,
                job_skills=data.get("job_skills", []),
                high_priority_missing=data.get("high_priority_missing", []),
                medium_priority_missing=data.get("medium_priority_missing", []),
                future_skills=data.get("future_skills", []),
                learning_roadmap=data.get("learning_roadmap", []),
            )

        except Exception as e:
            logger.error(f"SkillGapService failed: {e}")
            return SkillGapResult(
                resume_skills=resume_skills,
                job_skills=[],
                high_priority_missing=[],
                medium_priority_missing=[],
                future_skills=[],
                learning_roadmap=[],
            )
