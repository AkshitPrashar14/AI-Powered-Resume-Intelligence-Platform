"""
ResumeEmbedding ORM Model
==========================
Stores the FAISS index reference for each resume's embedding vector.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class ResumeEmbedding(Base):
    """
    resume_embeddings table.

    We store raw embedding vectors in FAISS (on disk) for fast ANN search.
    This table stores the *reference* (FAISS index ID + model name) so we
    know which vector belongs to which resume, and can invalidate the cache
    when a resume is updated.
    """

    __tablename__ = "resume_embeddings"

    # ── Primary Key ──────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign Key → Resumes ─────────────────────────────────
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        comment="Resume whose text was embedded",
    )

    # ── Embedding Metadata ────────────────────────────────────
    embedding_reference: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="FAISS internal index ID or disk path to the .npy file",
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="all-MiniLM-L6-v2",
        comment="Sentence Transformer model used to generate this embedding",
    )
    vector_dimension: Mapped[int] = mapped_column(
        nullable=False,
        default=384,
        comment="Dimensionality of the embedding vector",
    )
    chunk_index: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="For multi-chunk resumes: which chunk this embedding represents",
    )

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────
    resume: Mapped["Resume"] = relationship(  # noqa: F821
        "Resume",
        back_populates="embeddings",
        lazy="select",
    )

    # ── Indexes ───────────────────────────────────────────────
    __table_args__ = (
        Index("ix_embedding_resume_id", "resume_id"),
        Index("ix_embedding_model", "model_name"),
        {"comment": "FAISS embedding references for each resume chunk"},
    )

    def __repr__(self) -> str:
        return f"<ResumeEmbedding id={self.id} resume={self.resume_id} chunk={self.chunk_index}>"
