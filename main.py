"""
AI-Powered Resume Intelligence Platform
========================================
Main application entry point.

This module initializes and runs the FastAPI application with all
routers, middleware, and lifecycle events configured.
"""

import asyncio
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.routers import (
    analyze_router,
    ats_router,
    feedback_router,
    health_router,
    history_router,
    improve_router,
    match_router,
    upload_router,
)
from app.api.routers import jd_router, reports_router
from app.config import settings
from app.database.session import init_db


# ─────────────────────────────────────────────
# Configure Loguru (structured logging)
# ─────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)


# ─────────────────────────────────────────────
# Application Lifespan
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown lifecycle events.
    - Initializes DB on startup
    - Preloads embedding model to avoid cold start on first request
    - Connects to Redis (L1 cache)
    """
    logger.info("🚀 Starting AI Resume Intelligence Platform...")

    # Initialize database tables
    await init_db()
    logger.info("✅ Database initialized")

    # Preload SentenceTransformer embedding model (singleton — avoids cold start)
    from app.ai.embeddings.embedding_engine import EmbeddingEngine
    engine = EmbeddingEngine.get_instance()
    logger.info(f"✅ Embedding model loaded: {settings.EMBEDDING_MODEL} (dim={engine.dimension})")

    # Test Redis connection (L1 cache)
    from app.ai.cache.embedding_cache import _get_redis
    r = _get_redis()
    if r:
        logger.info(f"✅ Redis connected: {settings.REDIS_URL}")
    else:
        logger.warning("⚠️  Redis unavailable — using disk cache only (L2 fallback)")

    # Ensure required directories exist
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.EMBEDDING_CACHE_DIR, exist_ok=True)
    os.makedirs(settings.FAISS_INDEX_DIR, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    logger.info("✅ Directories ready")

    logger.info("🎯 Platform READY — Swagger UI: http://localhost:8000/docs")
    yield

    # Graceful shutdown
    logger.info("🛑 Shutting down platform gracefully...")


# ─────────────────────────────────────────────
# FastAPI App Factory
# ─────────────────────────────────────────────
def create_application() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance.
    """
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
## AI-Powered Resume Intelligence Platform

A production-grade platform that uses **Google Gemini**, **Sentence Transformers**,
**FAISS**, and a complete **RAG pipeline** to analyze resumes against job descriptions.

### Tech Stack
- 🤗 **Sentence Transformers** (all-MiniLM-L6-v2) for dense embeddings
- 🔍 **FAISS** for semantic vector search and Top-K retrieval
- 🤖 **RAG Pipeline** (Chunk → Embed → FAISS → Context → Gemini)
- ⚡ **Redis** (L1) + **Disk** (L2) hybrid embedding cache
- 📐 **Rule-based ATS Engine** — deterministic, reproducible scoring
- 🔐 **JWT Authentication** with bcrypt password hashing
- 🗄️ **PostgreSQL** with async SQLAlchemy + Alembic migrations

### Key Features
- 📄 **Resume Parsing** — PDF, DOCX, TXT with regex field extraction
- 🎯 **ATS Scoring** — Deterministic 100-point rule-based score
- 🔍 **Semantic Matching** — FAISS cosine similarity with per-category breakdown
- 🤖 **RAG Analysis** — Full retrieval pipeline with Gemini
- 💡 **Resume Improvement** — STAR-format bullet rewrites
- 🔑 **Keyword Optimizer** — ATS keyword injection suggestions
- 📊 **Skill Gap Detection** — Prioritized learning roadmap
- 📑 **JSON + PDF Reports** — Structured output + downloadable PDF
        """,
        openapi_tags=[
            {"name": "health", "description": "Health check endpoints"},
            {"name": "upload", "description": "Resume and job description upload"},
            {"name": "analyze", "description": "Full AI analysis pipeline (orchestrated)"},
            {"name": "ats", "description": "Standalone rule-based ATS scoring"},
            {"name": "match", "description": "Standalone semantic resume-JD matching"},
            {"name": "improve", "description": "STAR-format resume bullet improvement"},
            {"name": "feedback", "description": "Section-by-section recruiter feedback"},
            {"name": "history", "description": "Analysis history (user-wide and per-resume)"},
            {"name": "reports", "description": "Structured JSON and PDF reports"},
        ],
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS Middleware ───────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request Timing Middleware ─────────────────────────────
    @application.middleware("http")
    async def log_request_time(request: Request, call_next):
        import time
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.debug(
            f"[API] {request.method} {request.url.path} → "
            f"{response.status_code} ({elapsed:.0f}ms)"
        )
        return response

    # ── Register Routers ──────────────────────────────────────
    api_prefix = "/api/v1"

    # Core endpoints
    application.include_router(health_router.router, prefix=api_prefix, tags=["health"])
    application.include_router(upload_router.router, prefix=api_prefix, tags=["upload"])
    application.include_router(jd_router.router, prefix=api_prefix)
    application.include_router(analyze_router.router, prefix=api_prefix, tags=["analyze"])
    application.include_router(ats_router.router, prefix=api_prefix, tags=["ats"])
    application.include_router(match_router.router, prefix=api_prefix, tags=["match"])
    application.include_router(improve_router.router, prefix=api_prefix, tags=["improve"])
    application.include_router(feedback_router.router, prefix=api_prefix, tags=["feedback"])
    application.include_router(history_router.router, prefix=api_prefix)
    application.include_router(reports_router.router, prefix=api_prefix)

    # ── Global Exception Handler ──────────────────────────────
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"[API] Unhandled exception on {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again later."},
        )

    return application


app = create_application()


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
