# AI-Powered Resume Intelligence Platform

> A production-grade resume analysis system built with **FastAPI**, **Google Gemini**, **Sentence Transformers**, **FAISS**, and a full **RAG pipeline** — designed to impress recruiters at top-tier companies.

---

## Features

| Feature | Description |
|---|---|
| 📄 **Resume Parsing** | PDF (pdfplumber + PyMuPDF), DOCX, TXT |
| 🎯 **ATS Scoring** | AI-powered score out of 100 with sub-category breakdown |
| 🔍 **Semantic Matching** | FAISS cosine similarity between resume and JD |
| 🤖 **RAG Pipeline** | Chunk → Embed → Retrieve → Gemini → Structured Answer |
| 💡 **Resume Improvement** | STAR-format bullet rewrites with quantified achievements |
| 🔑 **Keyword Optimizer** | Missing ATS keywords, industry terms, action verbs |
| 📊 **Skill Gap Detection** | Prioritized learning roadmap (High / Medium / Future) |
| 📋 **Section Feedback** | Per-section scores + recruiter impression |
| 📑 **Download Report** | Full JSON intelligence report download |
| 🗃️ **Analysis History** | Per-resume analysis history from PostgreSQL |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                   │
│            frontend/app.py (port 8501)                  │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP REST
┌────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend                        │
│                main.py (port 8000)                      │
│                                                         │
│  /upload  /analyze  /ats-score  /match  /improve        │
│  /feedback  /history  /health                           │
└─────┬──────────────┬──────────────────┬─────────────────┘
      │              │                  │
┌─────▼──────┐ ┌────▼────────┐ ┌──────▼──────────────┐
│ PostgreSQL │ │   FAISS     │ │   Google Gemini API  │
│ (SQLAlch.  │ │ Vector DB   │ │   (gemini-1.5-flash) │
│ + Alembic) │ │ + Cache     │ │   + RAG Pipeline     │
└────────────┘ └─────────────┘ └──────────────────────┘
```

### RAG Pipeline

```
Resume Text
    │
    ▼
TextChunker (512-char, 50 overlap)
    │
    ▼
SentenceTransformer (all-MiniLM-L6-v2)
    │  Embedding Cache (MD5-keyed .pkl)
    ▼
FAISS Index (IndexFlatIP — cosine via L2-norm)
    │
    ▼
Query (Job Description)
    │
    ▼
Top-K Retrieval
    │
    ▼
Context Builder → Gemini Prompt
    │
    ▼
Gemini API (JSON response)
    │
    ▼
Structured Analysis Result
```

---

## Project Structure

```
resume-intelligence-platform/
├── main.py                          # FastAPI app entry point
├── requirements.txt
├── .env.example                     # Environment config template
├── alembic.ini                      # Alembic migration config
├── pytest.ini
│
├── app/
│   ├── config.py                    # Pydantic settings (singleton)
│   ├── api/
│   │   └── routers/
│   │       ├── health_router.py
│   │       ├── upload_router.py
│   │       ├── analyze_router.py
│   │       ├── ats_router.py
│   │       ├── match_router.py
│   │       ├── improve_router.py
│   │       ├── feedback_router.py
│   │       └── history_router.py
│   │
│   ├── services/
│   │   ├── analysis_service.py      # Orchestrator — runs all AI services
│   │   ├── ats_service.py
│   │   ├── match_service.py
│   │   ├── improve_service.py
│   │   ├── feedback_service.py
│   │   ├── skill_gap_service.py
│   │   ├── keyword_service.py
│   │   └── resume_service.py
│   │
│   ├── ai/
│   │   ├── gemini_client.py         # Async Gemini wrapper + retry + JSON extractor
│   │   ├── rag/
│   │   │   ├── chunker.py           # Paragraph-aware text chunker
│   │   │   ├── retriever.py         # FAISS IndexFlatIP retriever
│   │   │   └── rag_pipeline.py      # Full RAG orchestrator
│   │   ├── embeddings/
│   │   │   └── embedding_engine.py  # Singleton SentenceTransformer + batch embed
│   │   └── cache/
│   │       └── embedding_cache.py   # MD5-keyed disk cache for embeddings
│   │
│   ├── models/                      # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── resume.py
│   │   ├── job_description.py
│   │   ├── analysis.py
│   │   ├── embedding.py
│   │   └── report.py
│   │
│   ├── schemas/
│   │   └── schemas.py               # All Pydantic request/response schemas
│   │
│   ├── database/
│   │   ├── session.py               # Async engine + session factory
│   │   └── repositories/
│   │       ├── base.py              # Generic async CRUD repository
│   │       ├── user_repository.py
│   │       ├── resume_repository.py
│   │       ├── jd_repository.py
│   │       ├── analysis_repository.py
│   │       └── report_repository.py
│   │
│   ├── utils/
│   │   └── file_parser.py           # PDF/DOCX/TXT parser + field extractor
│   │
│   └── prompts/
│       └── templates.py             # All Gemini prompt templates
│
├── alembic/
│   ├── env.py                       # Alembic environment (autogenerate enabled)
│   ├── script.py.mako
│   └── versions/                    # Migration scripts go here
│
├── frontend/
│   └── app.py                       # Streamlit UI
│
└── tests/
    ├── conftest.py
    └── test_services.py
```

---

## Database Schema

```sql
users              → resumes (1:N, CASCADE)
users              → job_descriptions (1:N, CASCADE)
resumes            → analysis_history (1:N, CASCADE)
resumes            → resume_embeddings (1:N, CASCADE)
job_descriptions   → analysis_history (1:N, CASCADE)
analysis_history   → reports (1:1, CASCADE, UNIQUE)
```

All tables use **UUID primary keys**, **timestamped columns**, and **PostgreSQL indexes** on all foreign keys and frequently queried fields.

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Google Gemini API key

### 1. Clone & install dependencies

```bash
git clone <repo-url>
cd resume-intelligence-platform
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set:
#   GEMINI_API_KEY=your_key_here
#   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/resume_intelligence
#   DATABASE_URL_SYNC=postgresql+psycopg2://user:pass@localhost:5432/resume_intelligence
```

### 3. Create PostgreSQL database

```bash
psql -U postgres -c "CREATE DATABASE resume_intelligence;"
```

### 4. Run Alembic migrations

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### 5. Start the backend

```bash
uvicorn main:app --reload --port 8000
# Docs: http://localhost:8000/docs
```

### 6. Start the frontend

```bash
streamlit run frontend/app.py
# Opens: http://localhost:8501
```

### 7. Run tests

```bash
pytest tests/ -v
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/upload` | Upload resume (PDF/DOCX/TXT) |
| `POST` | `/api/v1/analyze` | Full AI analysis pipeline |
| `POST` | `/api/v1/ats-score` | ATS score only |
| `POST` | `/api/v1/match` | Semantic matching only |
| `POST` | `/api/v1/improve` | Resume bullet improvement |
| `POST` | `/api/v1/feedback` | Section-by-section feedback |
| `GET` | `/api/v1/history/{resume_id}` | Analysis history |

Full interactive docs at `http://localhost:8000/docs`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Framework** | FastAPI + Uvicorn |
| **AI / LLM** | Google Gemini 1.5 Flash |
| **Embeddings** | Sentence Transformers (all-MiniLM-L6-v2) |
| **Vector DB** | FAISS (IndexFlatIP) |
| **RAG** | Custom pipeline: chunk → embed → retrieve → generate |
| **Database** | PostgreSQL + SQLAlchemy 2.0 (async) + Alembic |
| **Validation** | Pydantic v2 |
| **Frontend** | Streamlit |
| **Parsing** | pdfplumber, PyMuPDF, python-docx |
| **Logging** | Loguru |
| **Testing** | pytest + pytest-asyncio |

---

## Future Improvements

- [ ] Multiple resume comparison
- [ ] Recruiter dashboard with aggregate analytics
- [ ] Resume ranking against multiple JDs
- [ ] Background job queue (Celery/RabbitMQ) for heavy async analysis
- [ ] Persistent shared FAISS index across distributed workers
- [ ] Resume versioning + diff view
