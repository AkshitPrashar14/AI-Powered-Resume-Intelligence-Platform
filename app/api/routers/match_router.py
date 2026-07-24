"""Match Router — delegates to AIOrchestrator"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.ai.orchestrator import AIOrchestrator
from app.database.session import get_db
from app.schemas.schemas import MatchResult
from app.models.user import User
from app.services.auth_service import get_current_active_user

router = APIRouter()


class MatchRequest(BaseModel):
    resume_id: uuid.UUID
    job_description: str
    resume_skills: List[str] = []


@router.post(
    "/match",
    response_model=MatchResult,
    summary="Semantic Matching",
    description="Compute semantic similarity (FAISS + SentenceTransformer) between resume and JD with per-category breakdown.",
)
async def match_resume(
    request: MatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Compute semantic similarity and skill overlap between resume and JD."""
    orchestrator = AIOrchestrator(db)
    try:
        return await orchestrator.run_match_only(
            request.resume_id,
            request.job_description,
            current_user.id,
            request.resume_skills,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
