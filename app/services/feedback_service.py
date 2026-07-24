"""
Section Feedback Service
=========================
Generates per-section recruiter-style feedback using Gemini.
"""

from loguru import logger

from app.ai.gemini_client import GeminiClient
from app.prompts.templates import PromptTemplates
from app.schemas.schemas import FeedbackResult, SectionFeedback


class FeedbackService:
    """
    Analyzes each resume section and produces structured feedback
    with a score, narrative, and actionable suggestions.
    """

    def __init__(self) -> None:
        self._gemini = GeminiClient()

    async def get_feedback(
        self, resume_text: str, job_description: str
    ) -> FeedbackResult:
        """
        Generate section-by-section feedback.

        Args:
            resume_text: Full resume text.
            job_description: Job description for context.

        Returns:
            FeedbackResult with per-section scores, feedback, and suggestions.
        """
        logger.info("Generating section feedback...")

        try:
            prompt = PromptTemplates.section_feedback(resume_text, job_description)
            data = await self._gemini.generate_json(prompt)

            sections = []
            for sec in data.get("sections", []):
                sections.append(
                    SectionFeedback(
                        section=sec.get("section", "Unknown"),
                        score=float(sec.get("score", 5.0)),
                        feedback=sec.get("feedback", ""),
                        suggestions=sec.get("suggestions", []),
                    )
                )

            return FeedbackResult(
                sections=sections,
                overall_verdict=data.get("overall_verdict", ""),
                recruiter_impression=data.get("recruiter_impression", ""),
            )

        except Exception as e:
            logger.error(f"FeedbackService failed: {e}")
            return self._default_feedback()

    def _default_feedback(self) -> FeedbackResult:
        """Returns a basic feedback object when Gemini is unavailable."""
        return FeedbackResult(
            sections=[
                SectionFeedback(
                    section="Summary",
                    score=5.0,
                    feedback="Could not analyze — please retry.",
                    suggestions=["Add a clear professional summary"],
                ),
                SectionFeedback(
                    section="Experience",
                    score=5.0,
                    feedback="Could not analyze — please retry.",
                    suggestions=["Use STAR format", "Add metrics"],
                ),
                SectionFeedback(
                    section="Skills",
                    score=5.0,
                    feedback="Could not analyze — please retry.",
                    suggestions=["Include relevant technical skills"],
                ),
            ],
            overall_verdict="Analysis unavailable — Gemini service error.",
            recruiter_impression="Please retry for recruiter impression.",
        )
