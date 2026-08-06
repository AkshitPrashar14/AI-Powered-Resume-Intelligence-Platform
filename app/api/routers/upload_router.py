"""
Upload Router
=============
Handles resume file uploads (PDF, DOCX, TXT).
"""

import uuid

from typing import List
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.schemas import UploadResumeResponse, ResumeResponse
from app.services.resume_service import ResumeService
from app.database.repositories.resume_repository import ResumeRepository

router = APIRouter()



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
        result = await service.upload_resume(file)
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

@router.get(
    "/upload/resumes",
    response_model=List[ResumeResponse],
    summary="Get all uploaded resumes",
)
async def get_all_resumes(db: AsyncSession = Depends(get_db)):
    repo = ResumeRepository(db)
    return await repo.get_all(limit=50)
