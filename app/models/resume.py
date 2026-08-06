"""
Resume ORM Model
================
Stores uploaded resumes with parsed text and file metadata.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Resume(Base):
    """
    Resumes table.

    Each row represents one uploaded resume file. Parsed text is
    stored for downstream embedding and analysis. Soft-delete is
    supported via the is_deleted flag.
    """

    __tablename__ = "resumes"

    # ── Primary Key ──────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── File Metadata ─────────────────────────────────────────
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original uploaded filename (e.g. my_resume.pdf)",
    )
    stored_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Filesystem path where the file is stored",
    )
    file_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="File extension: pdf, docx, or txt",
    )
    file_size_bytes: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="File size in bytes for validation auditing",
    )

    # ── Parsed Content ────────────────────────────────────────
    parsed_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full extracted text from the resume document",
    )
    candidate_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )
    candidate_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    candidate_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
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
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Soft delete flag — do not purge rows",
    )


    analyses: Mapped[list["AnalysisHistory"]] = relationship(  # noqa: F821
        "AnalysisHistory",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="select",
    )
    embeddings: Mapped[list["ResumeEmbedding"]] = relationship(  # noqa: F821
        "ResumeEmbedding",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ── Indexes ───────────────────────────────────────────────
    __table_args__ = (
        Index("ix_resumes_created_at", "created_at"),
        Index("ix_resumes_candidate_email", "candidate_email"),
        {"comment": "Uploaded resume documents with parsed content"},
    )

    def __repr__(self) -> str:
        return f"<Resume id={self.id} filename={self.original_filename}>"
