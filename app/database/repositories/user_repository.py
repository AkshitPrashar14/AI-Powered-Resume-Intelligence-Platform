"""
User Repository
===============
Domain-specific queries for the User model.
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.base import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):
    """
    Repository for User domain operations.

    Extends BaseRepository with user-specific queries such as
    email lookup (used during authentication).
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Find a user by their email address.

        Args:
            email: Email to search for (case-insensitive).

        Returns:
            User instance or None.
        """
        result = await self.db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Return True if the email is already registered."""
        user = await self.get_by_email(email)
        return user is not None

    async def get_active_users(self, limit: int = 100) -> list[User]:
        """Return only active (non-deactivated) users."""
        result = await self.db.execute(
            select(User).where(User.is_active == True).limit(limit)  # noqa: E712
        )
        return list(result.scalars().all())
