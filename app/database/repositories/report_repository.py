"""
Report Repository
=================
Domain-specific queries for the Report model.
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.base import BaseRepository
from app.models.report import Report


class ReportRepository(BaseRepository[Report]):
    """Repository for Report domain operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Report, db)

    async def get_by_analysis(self, analysis_id: uuid.UUID) -> Optional[Report]:
        """Fetch the report linked to a specific analysis."""
        result = await self.db.execute(
            select(Report).where(Report.analysis_id == analysis_id)
        )
        return result.scalar_one_or_none()

    async def get_with_analysis(self, analysis_id: uuid.UUID) -> Optional[Report]:
        """Fetch report and eagerly load the parent analysis for scores."""
        from sqlalchemy.orm import selectinload
        from app.models.analysis import AnalysisHistory

        result = await self.db.execute(
            select(Report)
            .options(selectinload(Report.analysis))
            .where(Report.analysis_id == analysis_id)
        )
        return result.scalar_one_or_none()
