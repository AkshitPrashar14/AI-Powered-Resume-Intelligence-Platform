"""
Resume Service
==============
Orchestrates file validation, parsing, and DB persistence for resume uploads.
"""

import os
import uuid
from pathlib import Path

from fastapi import UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.repositories.resume_repository import ResumeRepository
from app.database.repositories.user_repository import UserRepository
from app.models.resume import Resume
from app.schemas.schemas import ParsedResumeData, UploadResumeResponse
from app.utils.file_parser import FileParser


class ResumeService:
    """
    Handles the full resume upload lifecycle:
        1. Validate file type and size
        2. Save file to disk
        3. Parse content (PDF / DOCX / TXT)
        4. Persist metadata to PostgreSQL
        5. Return structured parsed data

    Args:
        db: Injected async database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._resume_repo = ResumeRepository(db)
        self._parser = FileParser()

    async def upload_resume(
        self, file: UploadFile, user_id: uuid.UUID
    ) -> UploadResumeResponse:
        """
        Validate, save, parse, and persist an uploaded resume file.

        Args:
            file: FastAPI UploadFile from multipart form.
            user_id: UUID of the authenticated user.

        Returns:
            UploadResumeResponse with resume_id and parsed data.

        Raises:
            ValueError: On invalid file type or size.
        """
        # ── 1. Validate extension ──────────────────────────────
        filename = file.filename or "upload.txt"
        ext = Path(filename).suffix.lower().strip(".")
        if ext not in settings.allowed_extensions_list:
            raise ValueError(
                f"Unsupported file type '.{ext}'. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )

        # ── 2. Read and validate size ─────────────────────────
        file_bytes = await file.read()
        if len(file_bytes) > settings.max_file_size_bytes:
            raise ValueError(
                f"File too large ({len(file_bytes) // 1024}KB). "
                f"Max: {settings.MAX_FILE_SIZE_MB}MB"
            )

        # ── 3. Save to disk ───────────────────────────────────
        resume_id = uuid.uuid4()
        stored_filename = f"{resume_id}.{ext}"
        stored_path = os.path.join(settings.UPLOAD_DIR, stored_filename)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        with open(stored_path, "wb") as f:
            f.write(file_bytes)
        logger.info(f"Saved resume to: {stored_path}")

        # ── 4. Parse content ──────────────────────────────────
        try:
            parsed: ParsedResumeData = self._parser.parse(file_bytes, filename)
        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            parsed = ParsedResumeData(raw_text="", name=None, email=None, phone=None)

        # ── 5. Persist to DB ──────────────────────────────────
        resume = await self._resume_repo.create(
            id=resume_id,
            user_id=user_id,
            original_filename=filename,
            stored_path=stored_path,
            file_type=ext,
            file_size_bytes=len(file_bytes),
            parsed_text=parsed.raw_text,
            candidate_name=parsed.name,
            candidate_email=parsed.email,
            candidate_phone=parsed.phone,
        )
        logger.info(f"Resume persisted: {resume.id}")

        return UploadResumeResponse(
            resume_id=resume.id,
            message="Resume uploaded and parsed successfully",
            parsed_data=parsed,
        )

    async def get_resume_text(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> str:
        """
        Retrieve parsed text for a resume by ID.

        Raises:
            ValueError: If resume not found or does not belong to user.
        """
        resume = await self._resume_repo.get_active(resume_id)
        if not resume or resume.user_id != user_id:
            raise ValueError(f"Resume {resume_id} not found")
        return resume.parsed_text or ""
