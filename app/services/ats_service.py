"""
Rule-Based ATS Scoring Engine
==============================
Deterministic ATS score computed entirely from rule-based heuristics.
Gemini is NEVER used to generate the numeric score — only to produce
human-readable explanations and improvement suggestions.

Score Breakdown (total = 100 points):
    Keyword Match        25 pts  — JD keywords found in resume
    Technical Skills     20 pts  — matched skills vs required
    Experience           15 pts  — years of experience, seniority
    Education            10 pts  — degree-level keywords
    Projects             10 pts  — projects section quality
    Action Verbs         10 pts  — strong action verb usage
    Resume Formatting    10 pts  — sections present, contact info

This design ensures:
    - Reproducible scores (same input → same output)
    - No Gemini API latency in the scoring path
    - Gemini enhances UX with explanations, not scores
"""

import re
import time
from typing import Dict, List, Set, Tuple

from loguru import logger

from app.ai.gemini_client import GeminiClient
from app.ai.cache.embedding_cache import HybridEmbeddingCache
from app.prompts.templates import PromptTemplates
from app.schemas.schemas import ATSScoreResult


# ── Scoring Constants ─────────────────────────────────────────────────────────
MAX_KEYWORD_SCORE: float = 25.0
MAX_SKILLS_SCORE: float = 20.0
MAX_EXPERIENCE_SCORE: float = 15.0
MAX_EDUCATION_SCORE: float = 10.0
MAX_PROJECTS_SCORE: float = 10.0
MAX_ACTION_VERBS_SCORE: float = 10.0
MAX_FORMAT_SCORE: float = 10.0

# Strong action verbs used by ATS systems
ACTION_VERBS: Set[str] = {
    "achieved", "architected", "automated", "built", "collaborated", "conceived",
    "created", "delivered", "deployed", "designed", "developed", "drove",
    "enhanced", "established", "executed", "improved", "increased", "integrated",
    "launched", "led", "managed", "mentored", "migrated", "optimized",
    "orchestrated", "owned", "pioneered", "reduced", "refactored", "resolved",
    "scaled", "spearheaded", "streamlined", "transformed", "upgraded",
}

# Education-related keywords
EDUCATION_KEYWORDS: Set[str] = {
    "bachelor", "master", "phd", "b.s", "m.s", "b.tech", "m.tech",
    "b.e", "m.e", "computer science", "engineering", "university", "college",
    "degree", "graduate", "undergraduate", "diploma",
}

# Experience-related keywords
EXPERIENCE_KEYWORDS: Set[str] = {
    "experience", "worked", "employment", "professional", "career",
    "position", "role", "internship", "job",
}

# Common technical skills for matching
COMMON_TECHNICAL_SKILLS: Set[str] = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "scala",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
    "react", "angular", "vue", "node.js", "django", "fastapi", "flask", "spring",
    "docker", "kubernetes", "aws", "gcp", "azure", "terraform", "ansible",
    "git", "ci/cd", "jenkins", "github actions", "gitlab", "kafka", "rabbitmq",
    "machine learning", "deep learning", "nlp", "pytorch", "tensorflow",
    "pandas", "numpy", "spark", "hadoop", "airflow", "dbt", "tableau",
    "rest api", "graphql", "microservices", "system design", "agile", "scrum",
    "linux", "bash", "data structures", "algorithms",
}


class RuleBasedATSEngine:
    """
    Deterministic ATS scoring engine.

    Computes the score using pure rule-based heuristics, then optionally
    calls Gemini for human-readable explanations.

    This ensures the numeric score is stable, reproducible, and fast —
    while Gemini provides the qualitative narrative.
    """

    def __init__(self) -> None:
        self._gemini = GeminiClient()
        self._cache = HybridEmbeddingCache()

    async def calculate_score(
        self, resume_text: str, job_description: str
    ) -> ATSScoreResult:
        """
        Calculate the ATS score for a resume against a job description.

        Steps:
            1. Run rule-based scoring (deterministic, fast)
            2. Check cache for Gemini explanation
            3. Call Gemini for explanations only (not scores)
            4. Return merged ATSScoreResult

        Args:
            resume_text: Full parsed resume text.
            job_description: Target job description text.

        Returns:
            ATSScoreResult with deterministic score + AI explanation.
        """
        t0 = time.perf_counter()
        logger.info("[ATS] Starting rule-based ATS calculation...")

        resume_lower = resume_text.lower()
        jd_lower = job_description.lower()

        # ── 1. Rule-based scoring ─────────────────────────────────────────────
        keyword_score, present_kw, missing_kw = self._score_keywords(resume_lower, jd_lower)
        skills_score, matching_skills, missing_skills = self._score_skills(resume_lower, jd_lower)
        experience_score = self._score_experience(resume_lower, jd_lower)
        education_score = self._score_education(resume_lower)
        projects_score = self._score_projects(resume_lower)
        action_verbs_score, found_verbs = self._score_action_verbs(resume_lower)
        format_score = self._score_formatting(resume_text)

        total = (
            keyword_score
            + skills_score
            + experience_score
            + education_score
            + projects_score
            + action_verbs_score
            + format_score
        )
        total = round(min(max(total, 0.0), 100.0), 1)

        score_elapsed = (time.perf_counter() - t0) * 1000
        logger.info(
            f"[ATS] Rule-based score: {total}/100 "
            f"(kw={keyword_score:.1f}, sk={skills_score:.1f}, "
            f"exp={experience_score:.1f}, edu={education_score:.1f}, "
            f"proj={projects_score:.1f}, verbs={action_verbs_score:.1f}, "
            f"fmt={format_score:.1f}) — {score_elapsed:.0f}ms"
        )

        # ── 2. Get Gemini explanations (cached) ───────────────────────────────
        recommendations = []
        breakdown: Dict = {
            "keyword_match": f"{keyword_score:.1f}/{MAX_KEYWORD_SCORE} — keyword overlap with JD",
            "technical_skills": f"{skills_score:.1f}/{MAX_SKILLS_SCORE} — skills match",
            "experience": f"{experience_score:.1f}/{MAX_EXPERIENCE_SCORE} — experience level",
            "education": f"{education_score:.1f}/{MAX_EDUCATION_SCORE} — education section",
            "projects": f"{projects_score:.1f}/{MAX_PROJECTS_SCORE} — projects section",
            "action_verbs": f"{action_verbs_score:.1f}/{MAX_ACTION_VERBS_SCORE} — strong verbs used",
            "formatting": f"{format_score:.1f}/{MAX_FORMAT_SCORE} — resume structure",
            "action_verbs_found": found_verbs,
        }

        try:
            import hashlib
            cache_key = hashlib.sha256(
                (resume_text[:2000] + job_description[:1000]).encode()
            ).hexdigest()
            cached_resp = self._cache.get_response(f"ats_expl:{cache_key}")

            if cached_resp:
                logger.debug("[ATS] Explanation cache HIT")
                recommendations = cached_resp.get("recommendations", [])
                breakdown.update(cached_resp.get("breakdown_extra", {}))
            else:
                prompt = PromptTemplates.ats_explanation(resume_text, job_description, total)
                data = await self._gemini.generate_json(prompt)
                recommendations = data.get("recommendations", [])
                breakdown.update({"ai_notes": data.get("weak_areas", "")})
                self._cache.set_response(
                    f"ats_expl:{cache_key}",
                    {"recommendations": recommendations, "breakdown_extra": {"ai_notes": data.get("weak_areas", "")}},
                )
        except Exception as e:
            logger.warning(f"[ATS] Gemini explanation failed (using fallback): {e}")
            recommendations = self._default_recommendations(missing_kw, missing_skills)

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(f"[ATS] Total time: {elapsed:.0f}ms")

        return ATSScoreResult(
            total_score=total,
            keyword_score=keyword_score,
            format_score=format_score,
            skills_score=skills_score,
            experience_score=experience_score,
            education_score=education_score,
            sections_score=format_score,  # alias
            action_verbs_score=action_verbs_score,
            breakdown=breakdown,
            missing_keywords=missing_kw[:15],
            present_keywords=present_kw[:15],
            recommendations=recommendations,
        )

    # ── Rule-Based Scoring Methods ────────────────────────────────────────────

    def _score_keywords(
        self, resume_lower: str, jd_lower: str
    ) -> Tuple[float, List[str], List[str]]:
        """
        Score keyword overlap between resume and JD.

        Returns:
            (score, present_keywords, missing_keywords)
        """
        # Extract meaningful words from JD (4+ chars, not stopwords)
        stopwords = {
            "with", "that", "this", "from", "have", "will", "your", "their",
            "what", "when", "where", "some", "been", "more", "also", "into",
            "they", "must", "team", "work", "able", "well", "good",
        }
        jd_words = set(re.findall(r"\b[a-z][a-z+#\.]{3,}\b", jd_lower))
        jd_words -= stopwords
        resume_words = set(re.findall(r"\b[a-z][a-z+#\.]{3,}\b", resume_lower))

        present = list(jd_words & resume_words)
        missing = list(jd_words - resume_words)

        if not jd_words:
            return 0.0, [], []

        ratio = len(present) / len(jd_words)
        score = min(ratio * MAX_KEYWORD_SCORE * 2.5, MAX_KEYWORD_SCORE)

        return round(score, 1), sorted(present)[:20], sorted(missing)[:20]

    def _score_skills(
        self, resume_lower: str, jd_lower: str
    ) -> Tuple[float, List[str], List[str]]:
        """
        Score technical skills match.

        Returns:
            (score, matching_skills, missing_skills)
        """
        jd_skills = {s for s in COMMON_TECHNICAL_SKILLS if s in jd_lower}
        resume_skills = {s for s in COMMON_TECHNICAL_SKILLS if s in resume_lower}

        if not jd_skills:
            return MAX_SKILLS_SCORE * 0.5, [], []

        matching = list(jd_skills & resume_skills)
        missing = list(jd_skills - resume_skills)
        ratio = len(matching) / len(jd_skills)
        score = min(ratio * MAX_SKILLS_SCORE * 1.5, MAX_SKILLS_SCORE)

        return round(score, 1), sorted(matching), sorted(missing)

    def _score_experience(self, resume_lower: str, jd_lower: str) -> float:
        """
        Score experience section quality and level match.
        """
        score = 0.0

        # Experience section exists
        if any(kw in resume_lower for kw in EXPERIENCE_KEYWORDS):
            score += 5.0

        # Years of experience detection
        years_match = re.findall(r"(\d+)\+?\s*years?", resume_lower)
        if years_match:
            max_years = max(int(y) for y in years_match)
            score += min(max_years * 1.5, 7.0)

        # Seniority keyword alignment
        seniority_levels = {
            "entry": ["junior", "entry", "associate", "intern", "fresher"],
            "mid": ["mid", "intermediate", "engineer", "developer"],
            "senior": ["senior", "lead", "principal", "staff", "architect"],
        }
        jd_level = "mid"
        for level, kws in seniority_levels.items():
            if any(kw in jd_lower for kw in kws):
                jd_level = level
                break

        resume_level = "mid"
        for level, kws in seniority_levels.items():
            if any(kw in resume_lower for kw in kws):
                resume_level = level
                break

        if jd_level == resume_level:
            score += 3.0
        elif abs(list(seniority_levels.keys()).index(jd_level) -
                 list(seniority_levels.keys()).index(resume_level)) <= 1:
            score += 1.5

        return round(min(score, MAX_EXPERIENCE_SCORE), 1)

    def _score_education(self, resume_lower: str) -> float:
        """Score education section."""
        score = 0.0
        found = [kw for kw in EDUCATION_KEYWORDS if kw in resume_lower]
        if found:
            score = min(len(found) * 2.5, MAX_EDUCATION_SCORE)
        return round(score, 1)

    def _score_projects(self, resume_lower: str) -> float:
        """Score projects section presence and quality."""
        score = 0.0
        if "project" in resume_lower:
            score += 4.0
        # GitHub, URLs, links suggest real projects
        if "github" in resume_lower or "http" in resume_lower:
            score += 3.0
        # Technical terms in projects section add credibility
        tech_terms = sum(1 for s in COMMON_TECHNICAL_SKILLS if s in resume_lower)
        score += min(tech_terms * 0.3, 3.0)
        return round(min(score, MAX_PROJECTS_SCORE), 1)

    def _score_action_verbs(self, resume_lower: str) -> Tuple[float, List[str]]:
        """
        Score action verb usage.

        Returns:
            (score, list_of_found_verbs)
        """
        found = [v for v in ACTION_VERBS if v in resume_lower]
        score = min(len(found) * 1.25, MAX_ACTION_VERBS_SCORE)
        return round(score, 1), found

    def _score_formatting(self, resume_text: str) -> float:
        """
        Score resume formatting and structure.

        Checks: contact info, key sections, length.
        """
        score = 0.0
        resume_lower = resume_text.lower()

        # Contact info
        if re.search(r"[a-z0-9.]+@[a-z0-9.]+\.[a-z]{2,}", resume_lower):
            score += 1.5  # Email
        if re.search(r"\+?\d[\d\s\-]{8,}", resume_text):
            score += 1.0  # Phone

        # Essential sections
        section_checks = {
            "education": 1.5,
            "experience": 1.5,
            "skills": 1.5,
            "summary": 1.0,
            "project": 1.0,
            "achievement": 0.5,
            "certification": 0.5,
        }
        for kw, pts in section_checks.items():
            if kw in resume_lower:
                score += pts

        return round(min(score, MAX_FORMAT_SCORE), 1)

    def _default_recommendations(
        self, missing_kw: List[str], missing_skills: List[str]
    ) -> List[str]:
        """Fallback rule-based recommendations when Gemini is unavailable."""
        recs = []
        if missing_kw:
            recs.append(f"Add these keywords from the JD: {', '.join(missing_kw[:5])}")
        if missing_skills:
            recs.append(f"Develop these missing skills: {', '.join(missing_skills[:5])}")
        recs += [
            "Quantify your achievements with specific numbers and percentages",
            "Use strong action verbs at the start of every bullet point",
            "Ensure all core sections (Summary, Experience, Skills, Education) are present",
        ]
        return recs


# ── Legacy alias so existing code continues to work ───────────────────────────
ATSService = RuleBasedATSEngine
