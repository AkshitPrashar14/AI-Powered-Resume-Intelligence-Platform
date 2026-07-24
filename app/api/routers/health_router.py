"""Health Check Router"""
from datetime import datetime, timezone
from fastapi import APIRouter
from app.schemas.schemas import HealthResponse
from app.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Health Check")
async def health_check():
    """Returns application health status."""
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
