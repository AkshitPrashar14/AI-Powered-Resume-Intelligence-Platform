"""
Pydantic Schemas
================
Request/response models for all API endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ─────────────────────────────────────────────
# Common
# ─────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None


# ─────────────────────────────────────────────
# User Schemas
# ─────────────────────────────────────────────
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ─────────────────────────────────────────────
# Resume Schemas
# ─────────────────────────────────────────────
class ResumeResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_type: str
    candidate_name: Optional[str]
    candidate_email: Optional[str]
    candidate_phone: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ParsedResumeData(BaseModel):
    """Structured extracted resume data returned after parsing."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    summary: Optional[str] = None
    education: List[str] = []
    experience: List[str] = []
    skills: List[str] = []
    projects: List[str] = []
    certifications: List[str] = []
    achievements: List[str] = []
    links: List[str] = []
    raw_text: str = ""


class UploadResumeResponse(BaseModel):
    resume_id: uuid.UUID
    message: str
    parsed_data: ParsedResumeData


# ─────────────────────────────────────────────
# Job Description Schemas
# ─────────────────────────────────────────────
class JobDescriptionCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    description: str = Field(..., min_length=5)


class JobDescriptionResponse(BaseModel):
    id: uuid.UUID
    title: str
    company: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Analysis Schemas
# ─────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    resume_id: uuid.UUID
    job_description: str = Field(..., min_length=5, description="Raw JD text")
    job_title: Optional[str] = None
    company: Optional[str] = None


class ATSScoreResult(BaseModel):
    total_score: float = Field(..., ge=0, le=100)
    keyword_score: float
    format_score: float
    skills_score: float
    experience_score: float
    education_score: float
    sections_score: float
    action_verbs_score: float
    breakdown: Dict[str, Any] = {}
    missing_keywords: List[str] = []
    present_keywords: List[str] = []
    recommendations: List[str] = []


class MatchResult(BaseModel):
    similarity_percentage: float = Field(..., ge=0, le=100)
    matching_skills: List[str] = []
    missing_skills: List[str] = []
    important_missing_keywords: List[str] = []
    match_verdict: str = ""


class SkillGapResult(BaseModel):
    resume_skills: List[str] = []
    job_skills: List[str] = []
    high_priority_missing: List[str] = []
    medium_priority_missing: List[str] = []
    future_skills: List[str] = []
    learning_roadmap: List[Dict[str, str]] = []


class ImprovedBullet(BaseModel):
    original: str
    improved: str
    explanation: str


class ImproveResult(BaseModel):
    improved_bullets: List[ImprovedBullet] = []
    overall_suggestions: List[str] = []


class SectionFeedback(BaseModel):
    section: str
    score: float
    feedback: str
    suggestions: List[str] = []


class FeedbackResult(BaseModel):
    sections: List[SectionFeedback] = []
    overall_verdict: str = ""
    recruiter_impression: str = ""


class KeywordResult(BaseModel):
    missing_ats_keywords: List[str] = []
    industry_terms: List[str] = []
    action_verbs: List[str] = []
    modern_technologies: List[str] = []
    insertion_suggestions: List[Dict[str, str]] = []


class FullAnalysisResult(BaseModel):
    analysis_id: uuid.UUID
    ats_score: ATSScoreResult
    match_result: MatchResult
    skill_gap: SkillGapResult
    improve_result: ImproveResult
    feedback: FeedbackResult
    keyword_result: KeywordResult
    strengths: List[str] = []
    weaknesses: List[str] = []
    career_advice: str = ""
    interview_tips: List[str] = []
    career_roadmap: List[str] = []
    recruiter_verdict: str = ""


# ─────────────────────────────────────────────
# Report Schemas
# ─────────────────────────────────────────────
class ReportResponse(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    ats_score: Optional[float]
    similarity_score: Optional[float]
    strengths: Optional[List[str]]
    weaknesses: Optional[List[str]]
    recommendations: Optional[List[str]]
    interview_tips: Optional[List[str]]
    career_roadmap: Optional[List[str]]
    recruiter_verdict: Optional[str]
    generated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# History Schemas
# ─────────────────────────────────────────────
class HistoryItem(BaseModel):
    analysis_id: uuid.UUID
    resume_filename: str
    job_title: Optional[str]
    ats_score: Optional[float]
    similarity_score: Optional[float]
    status: str
    created_at: datetime
