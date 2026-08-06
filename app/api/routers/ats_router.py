"""ATS Score Router — delegates to AIOrchestrator"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.ai.orchestrator import AIOrchestrator
from app.database.session import get_db
from app.schemas.schemas import ATSScoreResult

router = APIRouter()


class ATSRequest(BaseModel):
    resume_id: uuid.UUID
    job_description: str


@router.post(
    "/ats-score",
    response_model=ATSScoreResult,
    summary="ATS Score Only",
    description="Calculate deterministic rule-based ATS score (0-100). Gemini explains but does NOT compute the score.",
)
async def get_ats_score(
    request: ATSRequest,
    db: AsyncSession = Depends(get_db),
):
    """Calculate ATS score for a resume against a job description."""
    orchestrator = AIOrchestrator(db)
    try:
        return await orchestrator.run_ats_only(
            request.resume_id, request.job_description
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
