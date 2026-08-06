"""
Job Description Upload Router
==============================
Endpoints for uploading and storing job descriptions.

POST /upload/job-description — Create a JD record in the database.
GET  /upload/job-descriptions — List JDs for the current user.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.jd_repository import JobDescriptionRepository
from app.database.session import get_db
from app.schemas.schemas import JobDescriptionCreate, JobDescriptionResponse

router = APIRouter(tags=["upload"])


@router.post(
    "/upload/job-description",
    response_model=JobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Job Description",
    description="Save a job description for use in resume analysis. Returns a jd_id that can be passed to the analysis endpoint.",
)
async def upload_job_description(
    jd_in: JobDescriptionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create and persist a job description record.

    The returned `id` can be used as `job_description_id` in analysis requests,
    or you can paste the raw text directly into the `/analyze` endpoint.
    """
    jd_repo = JobDescriptionRepository(db)
    try:
        jd = await jd_repo.create(
            title=jd_in.title,
            company=jd_in.company,
            description=jd_in.description,
        )
        logger.info(
            f"[JD] Created job description '{jd_in.title}' "
            f"— id={jd.id}"
        )
        return jd
    except Exception as e:
        logger.error(f"[JD] Failed to create job description: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save job description",
        )


@router.get(
    "/upload/job-descriptions",
    response_model=List[JobDescriptionResponse],
    summary="List Job Descriptions",
    description="List all job descriptions uploaded by the current user.",
)
async def list_job_descriptions(
    db: AsyncSession = Depends(get_db),
):
    """Return all job descriptions for the authenticated user."""
    jd_repo = JobDescriptionRepository(db)
    jds = await jd_repo.get_by_user()
    return jds
