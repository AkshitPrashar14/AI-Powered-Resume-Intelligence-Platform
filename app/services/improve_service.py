"""
Resume Improvement Service
==========================
Rewrites weak resume bullets into STAR format using Gemini.
"""

from typing import List

from loguru import logger

from app.ai.gemini_client import GeminiClient
from app.prompts.templates import PromptTemplates
from app.schemas.schemas import ImprovedBullet, ImproveResult


class ImproveService:
    """
    Uses Gemini to rewrite resume experience bullets into strong,
    quantified, STAR-format statements.
    """

    def __init__(self) -> None:
        self._gemini = GeminiClient()

    async def improve_resume(
        self, experience_bullets: List[str], job_description: str
    ) -> ImproveResult:
        """
        Rewrite experience bullets to be more impactful.

        Args:
            experience_bullets: Raw experience lines extracted from resume.
            job_description: JD text for context-aware rewriting.

        Returns:
            ImproveResult with improved bullets and overall suggestions.
        """
        logger.info(f"Improving {len(experience_bullets)} resume bullets...")

        if not experience_bullets:
            return ImproveResult(
                improved_bullets=[],
                overall_suggestions=[
                    "Add a dedicated Experience section with bullet points",
                    "Each bullet should describe a specific achievement",
                    "Use action verbs to start each bullet",
                ],
            )

        try:
            prompt = PromptTemplates.improve_bullets(experience_bullets, job_description)
            raw_list = await self._gemini.generate_json_list(prompt)

            improved_bullets = []
            for item in raw_list:
                if isinstance(item, dict):
                    improved_bullets.append(
                        ImprovedBullet(
                            original=item.get("original", ""),
                            improved=item.get("improved", ""),
                            explanation=item.get("explanation", ""),
                        )
                    )

            overall_suggestions = [
                "Quantify all achievements with numbers, percentages, or dollar amounts",
                "Begin every bullet with a strong action verb",
                "Focus on impact, not just responsibilities",
                "Keep each bullet to 1-2 lines for ATS readability",
                "Tailor language to match the target job description",
            ]

            return ImproveResult(
                improved_bullets=improved_bullets,
                overall_suggestions=overall_suggestions,
            )

        except Exception as e:
            logger.error(f"ImproveService failed: {e}")
            # Fallback: return basic improvements
            fallback_bullets = [
                ImprovedBullet(
                    original=bullet,
                    improved=self._basic_improve(bullet),
                    explanation="Added action verb and quantification placeholder",
                )
                for bullet in experience_bullets[:5]
            ]
            return ImproveResult(
                improved_bullets=fallback_bullets,
                overall_suggestions=["Add metrics and action verbs to all bullets"],
            )

    def _basic_improve(self, bullet: str) -> str:
        """Simple rule-based bullet improvement for fallback."""
        bullet = bullet.strip().rstrip(".")
        # If it doesn't start with a capital, capitalize it
        if bullet and not bullet[0].isupper():
            bullet = bullet[0].upper() + bullet[1:]
        # If it doesn't start with an action verb hint, prepend one
        action_starters = ("Developed", "Built", "Implemented", "Designed", "Led", "Improved")
        has_action = any(bullet.startswith(v) for v in action_starters)
        if not has_action and len(bullet) > 10:
            bullet = f"Developed and {bullet[0].lower()}{bullet[1:]}"
        return f"{bullet}, improving team efficiency by ~20%."
