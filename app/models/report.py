"""
Report ORM Model
================
Stores the full AI-generated intelligence report for each analysis run.
Reports are stored as structured JSON; PDFs are generated on demand.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Report(Base):
    """
    reports table.

    1:1 with AnalysisHistory. Stores the full structured Gemini output:
    strengths, weaknesses, recommendations, improved resume bullets,
    interview tips, career roadmap, and the full JSON report blob.
    """

    __tablename__ = "reports"

    # ── Primary Key ──────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign Key → AnalysisHistory (1:1) ──────────────────
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_history.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Enforces 1:1
        comment="The analysis run this report was generated from",
    )

    # ── Report Sections (JSON-serialized strings) ─────────────
    strengths: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON list of resume strengths identified by Gemini",
    )
    weaknesses: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON list of weaknesses / areas to improve",
    )
    recommendations: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON list of AI-generated improvement recommendations",
    )
    improved_resume: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON map of original → improved bullet points (STAR format)",
    )
    interview_tips: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON list of interview preparation tips",
    )
    career_roadmap: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON structured career development roadmap",
    )
    skill_gaps: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON map of high/medium/future priority missing skills",
    )
    keyword_suggestions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON list of missing ATS keywords to add",
    )
    section_feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON map of per-section feedback (Experience, Education, etc.)",
    )
    recruiter_verdict: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Short plain-text recruiter-style final verdict",
    )
    full_report_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full structured JSON report blob — consumed by frontend",
    )

    # ── Timestamps ────────────────────────────────────────────
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────
    analysis: Mapped["AnalysisHistory"] = relationship(  # noqa: F821
        "AnalysisHistory",
        back_populates="report",
        lazy="select",
    )

    # ── Indexes ───────────────────────────────────────────────
    __table_args__ = (
        Index("ix_reports_analysis_id", "analysis_id"),
        Index("ix_reports_generated_at", "generated_at"),
        {"comment": "Full AI-generated intelligence reports per analysis"},
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id} analysis={self.analysis_id}>"
