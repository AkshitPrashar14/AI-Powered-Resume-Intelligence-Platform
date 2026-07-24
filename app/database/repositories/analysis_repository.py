"""
AnalysisHistory Repository
"""
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.base import BaseRepository
from app.models.analysis import AnalysisHistory


class AnalysisRepository(BaseRepository[AnalysisHistory]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(AnalysisHistory, db)

    async def get_by_resume(self, resume_id: uuid.UUID, limit: int = 20) -> List[AnalysisHistory]:
        result = await self.db.execute(
            select(AnalysisHistory)
            .where(AnalysisHistory.resume_id == resume_id)
            .order_by(AnalysisHistory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_with_report(self, analysis_id: uuid.UUID) -> Optional[AnalysisHistory]:
        result = await self.db.execute(
            select(AnalysisHistory)
            .options(selectinload(AnalysisHistory.report))
            .where(AnalysisHistory.id == analysis_id)
        )
        return result.scalar_one_or_none()

    async def get_completed_by_resume(self, resume_id: uuid.UUID) -> List[AnalysisHistory]:
        result = await self.db.execute(
            select(AnalysisHistory)
            .where(
                AnalysisHistory.resume_id == resume_id,
                AnalysisHistory.status == "completed",
            )
            .order_by(AnalysisHistory.created_at.desc())
        )
        return list(result.scalars().all())
