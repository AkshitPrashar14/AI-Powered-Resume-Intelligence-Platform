"""
App Models Package.
Imports all models so Alembic's autogenerate can detect them.
"""

from app.models.analysis import AnalysisHistory
from app.models.embedding import ResumeEmbedding
from app.models.job_description import JobDescription
from app.models.report import Report
from app.models.resume import Resume

__all__ = [
    "Resume",
    "JobDescription",
    "AnalysisHistory",
    "ResumeEmbedding",
    "Report",
]
