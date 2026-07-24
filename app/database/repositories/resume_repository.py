"""
Resume Repository
"""
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.base import BaseRepository
from app.models.resume import Resume


class ResumeRepository(BaseRepository[Resume]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Resume, db)

    async def get_by_user(self, user_id: uuid.UUID, limit: int = 50) -> List[Resume]:
        result = await self.db.execute(
            select(Resume)
            .where(Resume.user_id == user_id, Resume.is_deleted == False)  # noqa
            .order_by(Resume.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_active(self, resume_id: uuid.UUID) -> Optional[Resume]:
        result = await self.db.execute(
            select(Resume).where(Resume.id == resume_id, Resume.is_deleted == False)  # noqa
        )
        return result.scalar_one_or_none()

    async def soft_delete(self, resume_id: uuid.UUID) -> bool:
        instance = await self.get_by_id(resume_id)
        if not instance:
            return False
        instance.is_deleted = True
        self.db.add(instance)
        await self.db.flush()
        return True
