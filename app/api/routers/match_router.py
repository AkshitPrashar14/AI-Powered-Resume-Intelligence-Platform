"""Match Router — delegates to AIOrchestrator"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.ai.orchestrator import AIOrchestrator
from app.database.session import get_db
from app.schemas.schemas import MatchResult

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
):
    """Compute semantic similarity and skill overlap between resume and JD."""
    orchestrator = AIOrchestrator(db)
    try:
        return await orchestrator.run_match_only(
            request.resume_id,
            request.job_description,
            request.resume_skills,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
