"""
Database Session Management
============================
Async SQLAlchemy engine and session factory with connection pooling.
Provides FastAPI dependency injection for DB sessions.
"""

from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ─────────────────────────────────────────────
# Base ORM Class
# ─────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base class.
    All ORM models inherit from this.
    """
    pass


# ─────────────────────────────────────────────
# Async Engine (singleton)
# ─────────────────────────────────────────────
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Verifies connections before checkout (handles stale connections)
)

# ─────────────────────────────────────────────
# Session Factory
# ─────────────────────────────────────────────
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy loading issues after commit
    autocommit=False,
    autoflush=False,
)


# ─────────────────────────────────────────────
# Database Initialization
# ─────────────────────────────────────────────
async def init_db() -> None:
    """
    Verify database connectivity on startup.
    Actual schema creation is handled by Alembic migrations.
    """
    try:
        async with engine.connect() as conn:
            logger.info("✅ PostgreSQL connection verified")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise


# ─────────────────────────────────────────────
# FastAPI Dependency
# ─────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async DB session.
    Automatically commits on success or rolls back on exception.

    Usage:
        @router.post("/endpoint")
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
