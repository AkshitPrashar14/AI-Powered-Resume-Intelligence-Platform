"""Feedback Router — delegates to AIOrchestrator"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.ai.orchestrator import AIOrchestrator
from app.database.session import get_db
from app.schemas.schemas import FeedbackResult
from app.models.user import User
from app.services.auth_service import get_current_active_user

router = APIRouter()


class FeedbackRequest(BaseModel):
    resume_id: uuid.UUID
    job_description: str


@router.post(
    "/feedback",
    response_model=FeedbackResult,
    summary="Section Feedback",
    description="Generate per-section recruiter-style feedback with scores and improvement suggestions.",
)
async def get_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Generate per-section recruiter-style feedback."""
    orchestrator = AIOrchestrator(db)
    try:
        return await orchestrator.run_feedback_only(
            request.resume_id, request.job_description, current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
