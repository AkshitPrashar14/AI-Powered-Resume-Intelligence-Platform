"""
JobDescription Repository
"""
import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.base import BaseRepository
from app.models.job_description import JobDescription


class JobDescriptionRepository(BaseRepository[JobDescription]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(JobDescription, db)

    async def get_all(self, limit: int = 50) -> List[JobDescription]:
        result = await self.db.execute(
            select(JobDescription)
            .order_by(JobDescription.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
