"""
Upload Router
=============
Handles resume file uploads (PDF, DOCX, TXT).
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.schemas import UploadResumeResponse
from app.services.resume_service import ResumeService

router = APIRouter()

from app.models.user import User
from app.services.auth_service import get_current_active_user


@router.post(
    "/upload",
    response_model=UploadResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Resume",
    description="Upload a resume file (PDF, DOCX, or TXT). Returns parsed content and a resume_id for subsequent analysis.",
)
async def upload_resume(
    file: UploadFile = File(..., description="Resume file — PDF, DOCX, or TXT"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload and parse a resume file.

    - Validates file type and size
    - Extracts text using pdfplumber / python-docx
    - Persists file metadata to PostgreSQL
    - Returns structured parsed fields + resume_id
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    service = ResumeService(db)
    try:
        result = await service.upload_resume(file, user_id=current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process resume. Please try again.",
        )
