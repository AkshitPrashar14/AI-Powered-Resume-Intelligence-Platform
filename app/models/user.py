"""
User ORM Model
==============
Represents application users with hashed password storage.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class User(Base):
    """
    Users table.

    Stores authenticated user accounts. Passwords are never stored
    in plaintext — only bcrypt hashes are persisted.
    """

    __tablename__ = "users"

    # ── Primary Key ──────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique user identifier (UUID v4)",
    )

    # ── Identity Fields ───────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="Full display name",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="Unique email address used for login",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt-hashed password — never store plaintext",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Soft-disable account without deleting",
    )

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────
    resumes: Mapped[list["Resume"]] = relationship(  # noqa: F821
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    job_descriptions: Mapped[list["JobDescription"]] = relationship(  # noqa: F821
        "JobDescription",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ── Indexes ───────────────────────────────────────────────
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_created_at", "created_at"),
        {"comment": "Application user accounts"},
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
