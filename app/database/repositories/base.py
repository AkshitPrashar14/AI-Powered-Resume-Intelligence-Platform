"""
Base Repository
===============
Generic async repository implementing common CRUD operations.
All domain repositories inherit from this class.
"""

import uuid
from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic async CRUD repository.

    Provides create, read, update, delete operations for any SQLAlchemy model.
    Concrete repositories extend this and add domain-specific queries.

    Args:
        model: The SQLAlchemy ORM model class.
        db: The injected async database session.
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def create(self, **kwargs: Any) -> ModelType:
        """
        Create and persist a new model instance.

        Args:
            **kwargs: Field values for the model.

        Returns:
            The newly created and persisted model instance.
        """
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()   # Flush to get DB-generated fields (e.g. id, created_at)
        await self.db.refresh(instance)
        return instance

    async def get_by_id(self, record_id: uuid.UUID) -> Optional[ModelType]:
        """
        Fetch a single record by its primary key (UUID).

        Returns:
            The model instance, or None if not found.
        """
        result = await self.db.execute(
            select(self.model).where(self.model.id == record_id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ModelType]:
        """
        Fetch all records with optional pagination.

        Args:
            limit: Maximum number of rows to return.
            offset: Number of rows to skip.

        Returns:
            List of model instances.
        """
        result = await self.db.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def update(self, record_id: uuid.UUID, **kwargs: Any) -> Optional[ModelType]:
        """
        Update fields on an existing record.

        Args:
            record_id: UUID of the record to update.
            **kwargs: Fields to update.

        Returns:
            The updated model instance, or None if not found.
        """
        instance = await self.get_by_id(record_id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, record_id: uuid.UUID) -> bool:
        """
        Hard-delete a record by ID.

        Returns:
            True if the record was deleted, False if not found.
        """
        instance = await self.get_by_id(record_id)
        if instance is None:
            return False
        await self.db.delete(instance)
        await self.db.flush()
        return True

    async def exists(self, record_id: uuid.UUID) -> bool:
        """Return True if a record with the given ID exists."""
        instance = await self.get_by_id(record_id)
        return instance is not None
