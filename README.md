# AI-Powered Resume Intelligence Platform

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![React](https://img.shields.io/badge/react-18.0+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)

An open-access, production-grade Applicant Tracking System (ATS) and Resume Analyzer. This platform uses **Google Gemini**, **Sentence Transformers**, **FAISS**, and a complete **RAG pipeline** to provide deep, actionable insights for job seekers and recruiters.

---

## 🌟 Key Features

*   **Rule-Based ATS Scoring**: Deterministic 100-point scoring algorithm evaluating formatting, keyword density, and structural integrity.
*   **Semantic Matching**: High-accuracy context matching between resumes and job descriptions using HuggingFace `all-MiniLM-L6-v2` embeddings and FAISS vector search.
*   **Skill Gap Analysis & Roadmaps**: Identifies missing critical skills and utilizes Google Gemini to generate prioritized learning roadmaps.
*   **STAR-Format Bullet Improvements**: AI-driven enhancement of experience bullets to maximize impact and recruiter readability.
*   **RAG-Powered Insights**: Full Retrieval-Augmented Generation pipeline (Chunk → Embed → FAISS → Context → Gemini) for tailored career advice and interview tips.
*   **Modern React UI**: A responsive, fast, and accessible single-page application built with Vite and React.
*   **No Authentication Required**: Completely open-access architecture allowing for frictionless, instant analysis.

---

## 🛠️ Technology Stack

### Backend
*   **Framework**: FastAPI (Async Python)
*   **Database**: PostgreSQL (SQLAlchemy + Alembic)
*   **Caching**: Redis (L1) + Local Disk (L2 Hybrid Cache)
*   **AI/ML**: Google Gemini API, SentenceTransformers, FAISS
*   **Document Parsing**: `pdfplumber`, `python-docx`

### Frontend
*   **Framework**: React (Vite)
*   **Routing**: React Router DOM
*   **Styling**: Pure CSS with Dynamic CSS Variables
*   **Charting**: Recharts

### Infrastructure
*   **Containerization**: Docker & Docker Compose
*   **Proxy/Web Server**: NGINX

---

## 🚀 Getting Started (Local Development)

### Prerequisites
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
*   A [Google Gemini API Key](https://aistudio.google.com/app/apikey).

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AkshitPrashar14/AI-Powered-Resume-Intelligence-Platform.git
   cd AI-Powered-Resume-Intelligence-Platform
   ```

2. **Configure Environment Variables:**
   Copy the example environment file and add your Gemini API Key.
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` and insert your `GEMINI_API_KEY`.*

3. **Start the Platform:**
   Use Docker Compose to build and orchestrate the frontend, backend, database, and cache containers.
   ```bash
   docker compose up -d --build
   ```

4. **Access the Application:**
   *   **Frontend (React)**: [http://localhost:3001](http://localhost:3001)
   *   **Backend API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🌐 Deployment (Production)

The platform is designed to be easily deployed to modern cloud providers.

1. **Database**: Provision a managed PostgreSQL instance via [Neon.tech](https://neon.tech/).
2. **Cache**: Provision a managed Redis instance via [Upstash](https://upstash.com/).
3. **Backend**: Deploy the FastAPI Docker container to [Render](https://render.com/) or Railway.
4. **Frontend**: Deploy the React/Vite application to [Vercel](https://vercel.com/) (Ensure you set the Root Directory to `frontend`).

*Make sure to supply the `DATABASE_URL`, `REDIS_URL`, and `VITE_API_URL` environment variables to your respective hosting environments.*

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
