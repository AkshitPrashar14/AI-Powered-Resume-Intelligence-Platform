"""
Reports Router
==============
Endpoints for accessing structured JSON reports and downloading PDFs.

GET  /reports/{analysis_id}          — Full JSON report
GET  /reports/{analysis_id}/download — PDF download
"""

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Response, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.analysis_repository import AnalysisRepository
from app.database.repositories.resume_repository import ResumeRepository
from app.database.session import get_db
from app.models.user import User
from app.services.auth_service import get_current_active_user
from app.services.report_service import ReportService

router = APIRouter(tags=["reports"])


@router.get(
    "/reports/{analysis_id}",
    summary="Get JSON Report",
    description="Retrieve the full structured JSON analysis report. Frontend consumes this for display.",
    response_model=Dict[str, Any],
)
async def get_report(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return the full JSON report for a completed analysis."""
    # Verify ownership via analysis → resume → user
    analysis_repo = AnalysisRepository(db)
    analysis = await analysis_repo.get_by_id(analysis_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get_active(analysis.resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    report_service = ReportService(db)
    report_data = await report_service.get_report_json(analysis_id)

    if not report_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found. Analysis may still be processing.",
        )

    return report_data


@router.get(
    "/reports/{analysis_id}/download",
    summary="Download PDF Report",
    description="Generate and download a professional PDF report for a completed analysis.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF report file",
        }
    },
)
async def download_pdf_report(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Generate and return a PDF report for downloading."""
    # Verify ownership
    analysis_repo = AnalysisRepository(db)
    analysis = await analysis_repo.get_by_id(analysis_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get_active(analysis.resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    report_service = ReportService(db)
    try:
        pdf_bytes = await report_service.generate_pdf(analysis_id)
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
            "Content-Disposition": f"attachment; filename=resume_report_{str(analysis_id)[:8]}.pdf"
        },
    )
