"""
Analysis Router
===============
Full AI analysis pipeline endpoint — delegates to AIOrchestrator.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestrator import AIOrchestrator
from app.database.session import get_db
from app.schemas.schemas import AnalyzeRequest, FullAnalysisResult
from app.models.user import User
from app.services.auth_service import get_current_active_user

router = APIRouter()


@router.post(
    "/analyze",
    response_model=FullAnalysisResult,
    summary="Full Resume Analysis",
    description=(
        "Run the complete AI pipeline via AIOrchestrator: "
        "ATS scoring (rule-based), semantic matching (FAISS), "
        "skill gap, improvements, feedback, keyword optimization, "
        "and RAG analysis (Chunk → Embed → FAISS → Gemini)."
    ),
)
async def analyze_resume(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Full analysis endpoint via AIOrchestrator.

    Pipeline (orchestrated):
    - Rule-based ATS Score (deterministic)
    - Semantic Match (SentenceTransformer + FAISS cosine)
    - Skill Gap Detection (Gemini)
    - Resume Improvement (Gemini — STAR format)
    - Section Feedback (Gemini)
    - Keyword Optimization (Gemini)
    - RAG Full Analysis (Chunk → Embed → FAISS → Context → Gemini)

    All results persisted to PostgreSQL.
    """
    orchestrator = AIOrchestrator(db)
    try:
        result = await orchestrator.run_full_analysis(
            resume_id=request.resume_id,
            job_description_text=request.job_description,
            user_id=current_user.id,
            job_title=request.job_title or "",
            company=request.company or "",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"[ANALYZE] Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )
