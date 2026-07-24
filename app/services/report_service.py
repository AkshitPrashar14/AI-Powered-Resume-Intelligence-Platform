"""
Report Service
==============
Generates structured JSON reports and PDF downloads for analysis results.

Report Storage Strategy:
    1. Reports are stored as structured JSON in the `reports.full_report_json` column
    2. Frontend consumes JSON for display
    3. PDF is generated on-demand from the JSON for downloading
    4. PDF is never stored on disk — generated in memory per request
"""

import json
import uuid
from io import BytesIO
from typing import Any, Dict, Optional

from loguru import logger
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.analysis_repository import AnalysisRepository
from app.database.repositories.report_repository import ReportRepository


class ReportService:
    """
    Handles report retrieval (JSON) and on-demand PDF generation.

    Args:
        db: Injected async database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._report_repo = ReportRepository(db)
        self._analysis_repo = AnalysisRepository(db)

    async def get_report_json(self, analysis_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve the full structured JSON report for an analysis.

        Args:
            analysis_id: UUID of the analysis.

        Returns:
            Parsed report dict, or None if not found.
        """
        report = await self._report_repo.get_by_analysis(analysis_id)
        if not report:
            return None

        # Fetch analysis for scores
        analysis = await self._analysis_repo.get_by_id(analysis_id)

        result = {
            "report_id": str(report.id),
            "analysis_id": str(analysis_id),
            "generated_at": report.generated_at.isoformat(),
            "ats_score": analysis.ats_score if analysis else None,
            "similarity_score": analysis.similarity_score if analysis else None,
            "strengths": json.loads(report.strengths or "[]"),
            "weaknesses": json.loads(report.weaknesses or "[]"),
            "recommendations": json.loads(report.recommendations or "[]"),
            "interview_tips": json.loads(report.interview_tips or "[]"),
            "career_roadmap": json.loads(report.career_roadmap or "[]"),
            "skill_gaps": json.loads(report.skill_gaps or "{}"),
            "keyword_suggestions": json.loads(report.keyword_suggestions or "[]"),
            "section_feedback": json.loads(report.section_feedback or "[]"),
            "improved_resume": json.loads(report.improved_resume or "[]"),
            "recruiter_verdict": report.recruiter_verdict or "",
        }

        # Include full report JSON if available
        if report.full_report_json:
            try:
                full = json.loads(report.full_report_json)
                result.update(full)
                result["ats_score"] = analysis.ats_score if analysis else None
                result["similarity_score"] = analysis.similarity_score if analysis else None
            except Exception:
                pass

        return result

    async def generate_pdf(self, analysis_id: uuid.UUID) -> bytes:
        """
        Generate a professional PDF report from the stored JSON data.

        PDF is generated in-memory — not stored to disk.

        Args:
            analysis_id: UUID of the analysis to generate a report for.

        Returns:
            PDF bytes ready for HTTP response.

        Raises:
            ValueError: If the report is not found.
        """
        report_data = await self.get_report_json(analysis_id)
        if not report_data:
            raise ValueError(f"Report for analysis {analysis_id} not found")

        logger.info(f"[REPORT] Generating PDF for analysis {analysis_id}...")

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=20,
            textColor=colors.HexColor("#1a1a2e"),
            spaceAfter=6,
        )
        h2_style = ParagraphStyle(
            "CustomH2",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#16213e"),
            spaceBefore=12,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "CustomBody",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#333333"),
            spaceAfter=4,
            leading=14,
        )
        bullet_style = ParagraphStyle(
            "Bullet",
            parent=body_style,
            leftIndent=15,
            bulletIndent=5,
        )

        elements = []

        # ── Title ──────────────────────────────────────────────────────────────
        elements.append(Paragraph("AI Resume Intelligence Report", title_style))
        elements.append(Paragraph(
            f"Analysis ID: {str(analysis_id)[:8]}…  |  Generated: {report_data.get('generated_at', 'N/A')[:10]}",
            body_style,
        ))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0f3460")))
        elements.append(Spacer(1, 12))

        # ── Score Summary Table ────────────────────────────────────────────────
        ats = report_data.get("ats_score") or 0
        if isinstance(ats, dict):
            ats = ats.get("total_score", 0)
        sim = report_data.get("similarity_score") or 0

        score_data = [
            ["Metric", "Score", "Rating"],
            ["ATS Score", f"{ats:.1f} / 100", "🟢 Strong" if ats >= 75 else "🟡 Average" if ats >= 50 else "🔴 Weak"],
            ["Semantic Match", f"{sim:.1f}%", "🟢 Excellent" if sim >= 75 else "🟡 Good" if sim >= 50 else "🔴 Low"],
        ]
        table = Table(score_data, colWidths=[3 * inch, 2 * inch, 2.5 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 16))

        # ── Recruiter Verdict ──────────────────────────────────────────────────
        verdict = report_data.get("recruiter_verdict", "")
        if verdict:
            elements.append(Paragraph("Recruiter Verdict", h2_style))
            elements.append(Paragraph(verdict, body_style))
            elements.append(Spacer(1, 8))

        # ── Strengths ─────────────────────────────────────────────────────────
        strengths = report_data.get("strengths", [])
        if strengths:
            elements.append(Paragraph("✅ Resume Strengths", h2_style))
            for s in strengths:
                elements.append(Paragraph(f"• {s}", bullet_style))
            elements.append(Spacer(1, 8))

        # ── Weaknesses ────────────────────────────────────────────────────────
        weaknesses = report_data.get("weaknesses", [])
        if weaknesses:
            elements.append(Paragraph("⚠️ Areas for Improvement", h2_style))
            for w in weaknesses:
                elements.append(Paragraph(f"• {w}", bullet_style))
            elements.append(Spacer(1, 8))

        # ── Recommendations ───────────────────────────────────────────────────
        recs = report_data.get("recommendations", [])
        if recs:
            elements.append(Paragraph("💡 Recommendations", h2_style))
            for r in recs:
                elements.append(Paragraph(f"• {r}", bullet_style))
            elements.append(Spacer(1, 8))

        # ── Interview Tips ────────────────────────────────────────────────────
        tips = report_data.get("interview_tips", [])
        if tips:
            elements.append(Paragraph("🎤 Interview Tips", h2_style))
            for t in tips:
                elements.append(Paragraph(f"• {t}", bullet_style))
            elements.append(Spacer(1, 8))

        # ── Career Roadmap ────────────────────────────────────────────────────
        roadmap = report_data.get("career_roadmap", [])
        if roadmap:
            elements.append(Paragraph("📈 Career Roadmap", h2_style))
            for i, step in enumerate(roadmap, 1):
                elements.append(Paragraph(f"Step {i}: {step}", bullet_style))
            elements.append(Spacer(1, 8))

        # ── Skill Gaps ────────────────────────────────────────────────────────
        skill_gaps = report_data.get("skill_gaps", {})
        if skill_gaps:
            elements.append(Paragraph("🔍 Skill Gap Analysis", h2_style))
            if skill_gaps.get("high"):
                elements.append(Paragraph("High Priority:", ParagraphStyle("bold", parent=body_style, fontName="Helvetica-Bold")))
                elements.append(Paragraph(", ".join(skill_gaps["high"]), body_style))
            if skill_gaps.get("medium"):
                elements.append(Paragraph("Medium Priority:", ParagraphStyle("bold2", parent=body_style, fontName="Helvetica-Bold")))
                elements.append(Paragraph(", ".join(skill_gaps["medium"]), body_style))
            elements.append(Spacer(1, 8))

        # ── Footer ────────────────────────────────────────────────────────────
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Paragraph(
            "Generated by AI-Powered Resume Intelligence Platform | Powered by Sentence Transformers, FAISS & Google Gemini",
            ParagraphStyle("footer", parent=body_style, fontSize=8, textColor=colors.grey),
        ))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        logger.info(f"[REPORT] PDF generated — {len(pdf_bytes)} bytes")
        return pdf_bytes
