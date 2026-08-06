"""
History Router
==============
Endpoints for browsing analysis history.

GET /history                      — All analyses for the current user (across all resumes)
GET /history/{resume_id}          — All analyses for a specific resume
GET /history/{resume_id}/report.pdf — Download PDF report for latest analysis
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.analysis_repository import AnalysisRepository
from app.database.repositories.resume_repository import ResumeRepository
from app.database.session import get_db
from app.schemas.schemas import HistoryItem
from app.services.report_service import ReportService

router = APIRouter(tags=["history"])


@router.get(
    "/history",
    response_model=List[HistoryItem],
    summary="User-Wide Analysis History",
    description="Retrieve all analysis runs across all resumes for the current user.",
)
async def get_all_history(
    db: AsyncSession = Depends(get_db),
):
    """Return all past analyses for the authenticated user."""
    resume_repo = ResumeRepository(db)
    analysis_repo = AnalysisRepository(db)

    # Get all resumes since platform is open access
    user_resumes = await resume_repo.get_all()
    if not user_resumes:
        return []

    all_history: List[HistoryItem] = []
    for resume in user_resumes:
        analyses = await analysis_repo.get_by_resume(resume.id)
        for a in analyses:
            # Fetch JD title if available
            job_title = None
            if a.job_description_id:
                try:
                    from app.database.repositories.jd_repository import JobDescriptionRepository
                    jd_repo = JobDescriptionRepository(db)
                    jd = await jd_repo.get_by_id(a.job_description_id)
                    if jd:
                        job_title = jd.title
                except Exception:
                    pass

            all_history.append(
                HistoryItem(
                    analysis_id=a.id,
                    resume_filename=resume.original_filename,
                    job_title=job_title,
                    ats_score=a.ats_score,
                    similarity_score=a.similarity_score,
                    status=a.status,
                    created_at=a.created_at,
                )
            )

    # Sort by created_at descending
    all_history.sort(key=lambda x: x.created_at, reverse=True)
    return all_history


@router.get(
    "/history/{resume_id}",
    response_model=List[HistoryItem],
    summary="Resume Analysis History",
    description="Retrieve all analysis runs for a specific resume.",
)
async def get_history(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return all past analyses for a specific resume."""
    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get_active(resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    analysis_repo = AnalysisRepository(db)
    analyses = await analysis_repo.get_by_resume(resume_id)

    history = []
    for a in analyses:
        job_title = None
        if a.job_description_id:
            try:
                from app.database.repositories.jd_repository import JobDescriptionRepository
                jd_repo = JobDescriptionRepository(db)
                jd = await jd_repo.get_by_id(a.job_description_id)
                if jd:
                    job_title = jd.title
            except Exception:
                pass

        history.append(
            HistoryItem(
                analysis_id=a.id,
                resume_filename=resume.original_filename,
                job_title=job_title,
                ats_score=a.ats_score,
                similarity_score=a.similarity_score,
                status=a.status,
                created_at=a.created_at,
            )
        )

    return history


@router.get(
    "/history/{resume_id}/report.pdf",
    summary="Download Latest PDF Report",
    description="Download a PDF report for the latest completed analysis of a resume.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF report file",
        }
    },
)
async def get_pdf_report(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate and return a PDF report for the latest analysis."""
    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get_active(resume_id)
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    analysis_repo = AnalysisRepository(db)
    analyses = await analysis_repo.get_completed_by_resume(resume_id)
    if not analyses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed analysis found for this resume",
        )

    latest_analysis = analyses[0]
    report_service = ReportService(db)

    try:
        pdf_bytes = await report_service.generate_pdf(latest_analysis.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"[REPORT] PDF generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=report_{latest_analysis.id}.pdf"
        },
    )
