"""Improve Router — delegates to AIOrchestrator"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.ai.orchestrator import AIOrchestrator
from app.database.session import get_db
from app.schemas.schemas import ImproveResult

router = APIRouter()


class ImproveRequest(BaseModel):
    resume_id: uuid.UUID
    job_description: str


@router.post(
    "/improve",
    response_model=ImproveResult,
    summary="Resume Improvement",
    description="Rewrite resume bullets into STAR format with quantified achievements using Gemini.",
)
async def improve_resume(
    request: ImproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rewrite resume bullets into STAR format with quantified achievements."""
    orchestrator = AIOrchestrator(db)
    try:
        return await orchestrator.run_improve_only(
            request.resume_id, request.job_description
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
