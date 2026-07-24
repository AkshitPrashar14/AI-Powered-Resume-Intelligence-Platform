"""
JobDescription ORM Model
========================
Stores job descriptions entered by users for matching against resumes.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class JobDescription(Base):
    """
    job_descriptions table.

    Each row represents one job description a user wants to match
    their resume against. A user may store multiple JDs for comparison.
    """

    __tablename__ = "job_descriptions"

    # ── Primary Key ──────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign Key → Users ───────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who created this job description",
    )

    # ── Job Details ───────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Job title (e.g., Senior Backend Engineer)",
    )
    company: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Hiring company name",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full job description text",
    )
    required_skills: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Extracted required skills (JSON-serialized list)",
    )
    experience_level: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="e.g., Entry, Mid, Senior, Lead",
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
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="job_descriptions",
        lazy="select",
    )
    analyses: Mapped[list["AnalysisHistory"]] = relationship(  # noqa: F821
        "AnalysisHistory",
        back_populates="job_description",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ── Indexes ───────────────────────────────────────────────
    __table_args__ = (
        Index("ix_jd_user_id", "user_id"),
        Index("ix_jd_created_at", "created_at"),
        Index("ix_jd_title", "title"),
        {"comment": "Job descriptions submitted by users"},
    )

    def __repr__(self) -> str:
        return f"<JobDescription id={self.id} title={self.title}>"
