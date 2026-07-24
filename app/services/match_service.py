"""
Enhanced Semantic Match Service
================================
Uses FAISS + SentenceTransformers to compute contextual similarity between
resume and job description, then identifies matching/missing skills with
per-category explanations.

Resume Matching returns:
    - semantic_similarity       (FAISS cosine, 0-100)
    - matching_skills           (found in both resume + JD)
    - missing_skills            (in JD but not resume)
    - missing_technologies      (tools/frameworks from JD not in resume)
    - keyword_match_pct         (keyword overlap %)
    - experience_match          (seniority level alignment)
    - education_match           (degree/field relevance)
    - overall_match_pct         (weighted aggregate score)
    - match_verdict             (human-readable verdict string)
    - explanations              (per-category explanations)
"""

import re
import time
from typing import Dict, List, Optional, Set, Tuple

from loguru import logger

from app.ai.cache.embedding_cache import HybridEmbeddingCache
from app.ai.embeddings.embedding_engine import EmbeddingEngine
from app.ai.gemini_client import GeminiClient
from app.prompts.templates import PromptTemplates
from app.schemas.schemas import MatchResult


# Technology stacks for "missing technologies" detection
TECH_STACKS: Set[str] = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "scala", "kotlin",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra", "sqlite",
    "react", "angular", "vue", "next.js", "svelte", "node.js", "express", "nestjs",
    "django", "fastapi", "flask", "spring boot", "rails", "laravel",
    "docker", "kubernetes", "helm", "terraform", "ansible", "puppet", "chef",
    "aws", "gcp", "azure", "firebase", "heroku", "vercel",
    "kafka", "rabbitmq", "celery", "airflow", "spark", "hadoop", "dbt",
    "pytorch", "tensorflow", "scikit-learn", "hugging face", "langchain",
    "graphql", "grpc", "rest", "websocket", "kafka streams",
    "jenkins", "github actions", "gitlab ci", "circleci", "argocd",
    "pandas", "numpy", "matplotlib", "plotly",
    "git", "jira", "confluence", "notion",
}

COMMON_SKILLS: Set[str] = {
    "python", "java", "javascript", "typescript", "c++", "go", "rust", "sql",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "react", "angular", "vue", "node.js", "django", "fastapi", "spring",
    "docker", "kubernetes", "aws", "gcp", "azure", "terraform", "ansible",
    "git", "ci/cd", "jenkins", "github actions", "kafka", "rabbitmq",
    "machine learning", "deep learning", "nlp", "pytorch", "tensorflow",
    "pandas", "numpy", "spark", "hadoop", "airflow",
    "rest api", "graphql", "microservices", "system design",
    "agile", "scrum", "linux", "bash", "data structures",
}


class MatchService:
    """
    Computes semantic similarity and skill overlap between resume and JD.

    Steps:
        1. Check similarity cache (Redis → Disk)
        2. Embed both texts with SentenceTransformer (L2-normalized)
        3. Cosine similarity via dot product (= cosine because normalized)
        4. Rule-based skill overlap detection
        5. Technology gap analysis
        6. Weighted overall match score
        7. Gemini for per-category explanations (cached)
        8. Return structured MatchResult
    """

    # Weights for the overall match percentage
    WEIGHTS = {
        "semantic": 0.40,
        "skills": 0.25,
        "keywords": 0.15,
        "experience": 0.10,
        "education": 0.10,
    }

    def __init__(self) -> None:
        self._engine = EmbeddingEngine.get_instance()
        self._cache = HybridEmbeddingCache()
        self._gemini = GeminiClient()

    async def compute_match(
        self,
        resume_text: str,
        job_description: str,
        resume_skills: Optional[List[str]] = None,
    ) -> MatchResult:
        """
        Compute full semantic and structural match between resume and JD.

        Args:
            resume_text: Full parsed resume text.
            job_description: Full job description text.
            resume_skills: Optional list of pre-extracted resume skills.

        Returns:
            MatchResult with similarity %, skill breakdown, and explanations.
        """
        t0 = time.perf_counter()
        logger.info("[MATCH] Starting semantic resume matching...")

        resume_lower = resume_text.lower()
        jd_lower = job_description.lower()
        resume_skills = resume_skills or []

        # ── 1. Semantic Similarity (FAISS-ready cosine) ────────────────────────
        sim_score = self._engine.similarity(
            resume_text[:3000],
            job_description[:3000],
        )
        sim_pct = round(sim_score * 100, 2)
        logger.info(f"[MATCH] Semantic similarity: {sim_pct:.1f}%")

        # ── 2. Skill Overlap ────────────────────────────────────────────────────
        jd_skills = {s for s in COMMON_SKILLS if s in jd_lower}
        resume_skill_set = {s.lower() for s in resume_skills}
        resume_skill_set |= {s for s in COMMON_SKILLS if s in resume_lower}

        matching_skills = sorted(jd_skills & resume_skill_set)
        missing_skills = sorted(jd_skills - resume_skill_set)
        skill_ratio = len(matching_skills) / max(len(jd_skills), 1)

        # ── 3. Missing Technologies ─────────────────────────────────────────────
        jd_tech = {t for t in TECH_STACKS if t in jd_lower}
        resume_tech = {t for t in TECH_STACKS if t in resume_lower}
        missing_technologies = sorted(jd_tech - resume_tech)

        # ── 4. Keyword Match ────────────────────────────────────────────────────
        stopwords = {"with", "that", "this", "from", "have", "will", "your", "their"}
        jd_words = set(re.findall(r"\b[a-z][a-z+#\.]{3,}\b", jd_lower)) - stopwords
        resume_words = set(re.findall(r"\b[a-z][a-z+#\.]{3,}\b", resume_lower)) - stopwords
        keyword_pct = round(
            len(jd_words & resume_words) / max(len(jd_words), 1) * 100, 1
        )

        # ── 5. Experience Match ─────────────────────────────────────────────────
        exp_match_pct = self._compute_experience_match(resume_lower, jd_lower)

        # ── 6. Education Match ──────────────────────────────────────────────────
        edu_match_pct = self._compute_education_match(resume_lower, jd_lower)

        # ── 7. Weighted Overall Score ───────────────────────────────────────────
        overall = (
            sim_pct * self.WEIGHTS["semantic"]
            + skill_ratio * 100 * self.WEIGHTS["skills"]
            + keyword_pct * self.WEIGHTS["keywords"]
            + exp_match_pct * self.WEIGHTS["experience"]
            + edu_match_pct * self.WEIGHTS["education"]
        )
        overall = round(min(max(overall, 0.0), 100.0), 1)

        # ── 8. Gemini Explanations (cached) ─────────────────────────────────────
        explanations: Dict[str, str] = {}
        try:
            import hashlib
            cache_key = hashlib.sha256(
                (resume_text[:2000] + job_description[:1000]).encode()
            ).hexdigest()
            cached = self._cache.get_response(f"match_expl:{cache_key}")

            if cached:
                logger.debug("[MATCH] Explanation cache HIT")
                explanations = cached
            else:
                prompt = PromptTemplates.match_explanation(
                    resume_text, job_description, sim_pct, matching_skills, missing_skills
                )
                data = await self._gemini.generate_json(prompt)
                explanations = {
                    "experience": data.get("experience_match_explanation", ""),
                    "education": data.get("education_match_explanation", ""),
                    "keywords": data.get("keyword_match_explanation", ""),
                    "overall_verdict": data.get("overall_verdict", ""),
                    "improvement_priority": str(data.get("improvement_priority", [])),
                }
                self._cache.set_response(f"match_expl:{cache_key}", explanations)
        except Exception as e:
            logger.warning(f"[MATCH] Gemini explanation failed: {e}")
            explanations = {"overall_verdict": self._generate_verdict(sim_pct, len(matching_skills), len(missing_skills))}

        verdict = explanations.get("overall_verdict") or self._generate_verdict(
            sim_pct, len(matching_skills), len(missing_skills)
        )

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(
            f"[MATCH] Complete — similarity={sim_pct:.1f}%, "
            f"overall={overall:.1f}%, elapsed={elapsed:.0f}ms"
        )

        return MatchResult(
            similarity_percentage=sim_pct,
            matching_skills=matching_skills,
            missing_skills=missing_skills,
            important_missing_keywords=missing_technologies[:10],
            match_verdict=verdict,
        )

    def _compute_experience_match(self, resume_lower: str, jd_lower: str) -> float:
        """
        Rule-based experience level match.

        Returns a percentage 0-100 indicating how well experience aligns.
        """
        seniority = {
            "entry": ["junior", "entry", "associate", "intern", "0-2", "fresher"],
            "mid": ["mid-level", "intermediate", "3-5", "3+ years", "4+ years"],
            "senior": ["senior", "lead", "principal", "staff", "7+", "10+", "architect"],
        }

        jd_level = self._detect_level(jd_lower, seniority)
        resume_level = self._detect_level(resume_lower, seniority)

        levels = list(seniority.keys())
        jd_idx = levels.index(jd_level)
        res_idx = levels.index(resume_level)

        diff = abs(jd_idx - res_idx)
        if diff == 0:
            return 100.0
        elif diff == 1:
            return 60.0
        else:
            return 25.0

    def _detect_level(self, text: str, seniority: dict) -> str:
        for level, kws in seniority.items():
            if any(kw in text for kw in kws):
                return level
        return "mid"

    def _compute_education_match(self, resume_lower: str, jd_lower: str) -> float:
        """
        Rule-based education match.

        Returns a percentage 0-100.
        """
        edu_levels = {
            "phd": ["phd", "doctorate", "ph.d"],
            "masters": ["master", "m.s", "m.tech", "mba"],
            "bachelors": ["bachelor", "b.s", "b.tech", "b.e", "undergraduate"],
            "any": ["degree", "education", "computer science", "engineering"],
        }

        jd_req = "any"
        for level, kws in edu_levels.items():
            if any(kw in jd_lower for kw in kws):
                jd_req = level
                break

        resume_edu = "none"
        for level, kws in edu_levels.items():
            if any(kw in resume_lower for kw in kws):
                resume_edu = level
                break

        # Hierarchy: phd > masters > bachelors > any > none
        hierarchy = ["none", "any", "bachelors", "masters", "phd"]
        jd_val = hierarchy.index(jd_req) if jd_req in hierarchy else 1
        res_val = hierarchy.index(resume_edu) if resume_edu in hierarchy else 0

        if res_val >= jd_val:
            return 100.0
        elif res_val == jd_val - 1:
            return 60.0
        elif res_val > 0:
            return 30.0
        else:
            return 0.0

    def _generate_verdict(
        self, similarity: float, matched: int, missing: int
    ) -> str:
        if similarity >= 80:
            return "Excellent match — your resume strongly aligns with this role."
        elif similarity >= 65:
            return "Good match — with a few targeted improvements you would be a strong candidate."
        elif similarity >= 50:
            return "Moderate match — significant skill gaps need to be addressed before applying."
        else:
            return "Low match — consider upskilling or targeting a better-fitting role."
