"""
Keyword Optimizer Service
==========================
Identifies missing ATS keywords, industry terms, and action verbs.
"""

from loguru import logger

from app.ai.gemini_client import GeminiClient
from app.prompts.templates import PromptTemplates
from app.schemas.schemas import KeywordResult


class KeywordService:
    """
    Analyzes resume vs JD to surface missing ATS keywords,
    industry-specific terms, action verbs, and modern technologies.
    """

    def __init__(self) -> None:
        self._gemini = GeminiClient()

    async def optimize_keywords(
        self, resume_text: str, job_description: str
    ) -> KeywordResult:
        """
        Identify keyword gaps and suggest improvements.

        Args:
            resume_text: Full parsed resume text.
            job_description: Job description text.

        Returns:
            KeywordResult with categorized missing keywords.
        """
        logger.info("Running keyword optimization...")

        try:
            prompt = PromptTemplates.keyword_optimizer(resume_text, job_description)
            data = await self._gemini.generate_json(prompt)

            return KeywordResult(
                missing_ats_keywords=data.get("missing_ats_keywords", []),
                industry_terms=data.get("industry_terms", []),
                action_verbs=data.get("action_verbs", []),
                modern_technologies=data.get("modern_technologies", []),
                insertion_suggestions=data.get("insertion_suggestions", []),
            )

        except Exception as e:
            logger.error(f"KeywordService failed: {e}")
            return KeywordResult(
                missing_ats_keywords=[],
                industry_terms=[],
                action_verbs=["achieved", "optimized", "designed", "implemented"],
                modern_technologies=[],
                insertion_suggestions=[],
            )
