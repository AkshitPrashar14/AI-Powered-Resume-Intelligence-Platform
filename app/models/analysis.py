"""
AnalysisHistory ORM Model
==========================
Stores every resume-vs-JD analysis run, capturing ATS and similarity scores.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class AnalysisHistory(Base):
    """
    analysis_history table.

    Captures the result of each resume × job-description analysis.
    One analysis may produce one Report (1:1 relationship).

    Scores are stored as floats so they can be averaged/compared over time.
    """

    __tablename__ = "analysis_history"

    # ── Primary Key ──────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign Keys ─────────────────────────────────────────
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        comment="The resume that was analysed",
    )
    job_description_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        comment="The JD the resume was matched against",
    )

    # ── Scores ────────────────────────────────────────────────
    ats_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="ATS score out of 100",
    )
    similarity_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Semantic similarity score 0–100 (FAISS cosine)",
    )
    keyword_match_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of JD keywords found in resume",
    )
    missing_skills_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON list of skills present in JD but missing from resume",
    )
    matched_skills_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON list of matched skills",
    )

    # ── Status ────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        default="pending",
        nullable=False,
        comment="pending | processing | completed | failed",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if status=failed",
    )

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When analysis finished (null if still running)",
    )

    # ── Relationships ─────────────────────────────────────────
    resume: Mapped["Resume"] = relationship(  # noqa: F821
        "Resume",
        back_populates="analyses",
        lazy="select",
    )
    job_description: Mapped["JobDescription"] = relationship(  # noqa: F821
        "JobDescription",
        back_populates="analyses",
        lazy="select",
    )
    report: Mapped["Report"] = relationship(  # noqa: F821
        "Report",
        back_populates="analysis",
        cascade="all, delete-orphan",
        uselist=False,  # 1:1
        lazy="select",
    )

    # ── Indexes ───────────────────────────────────────────────
    __table_args__ = (
        Index("ix_analysis_resume_id", "resume_id"),
        Index("ix_analysis_jd_id", "job_description_id"),
        Index("ix_analysis_created_at", "created_at"),
        Index("ix_analysis_status", "status"),
        {"comment": "Historical log of all resume analysis runs"},
    )

    def __repr__(self) -> str:
        return f"<AnalysisHistory id={self.id} ats={self.ats_score} sim={self.similarity_score}>"
