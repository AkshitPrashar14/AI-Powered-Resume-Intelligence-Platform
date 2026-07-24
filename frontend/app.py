"""
AI Resume Intelligence Platform — Streamlit Frontend
=====================================================
Multi-page professional dashboard with JWT authentication.
"""

import json
import os
import time

import requests
import streamlit as st

# ── Config ──────────────────────────────────────────────────────────────────
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="AI Resume Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background: #0a0e1a; }
.stApp { background: linear-gradient(135deg, #0a0e1a 0%, #0d1321 50%, #0a0e1a 100%); }
.metric-card {
    background: linear-gradient(135deg, #1a2035 0%, #1e2640 100%);
    border: 1px solid rgba(99,179,237,0.2);
    border-radius: 12px; padding: 20px; text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.score-excellent { color: #48bb78; font-size: 2.5rem; font-weight: 700; }
.score-good      { color: #ecc94b; font-size: 2.5rem; font-weight: 700; }
.score-low       { color: #fc8181; font-size: 2.5rem; font-weight: 700; }
.tag {
    display: inline-block;
    background: rgba(99,179,237,0.15);
    border: 1px solid rgba(99,179,237,0.3);
    border-radius: 20px; padding: 3px 12px;
    font-size: 0.8rem; color: #90cdf4; margin: 2px;
}
.tag-missing {
    background: rgba(252,129,129,0.15);
    border-color: rgba(252,129,129,0.3); color: #fc8181;
}
.stButton > button {
    background: linear-gradient(135deg, #3182ce, #2b6cb0);
    color: white; border: none; border-radius: 8px;
    padding: 0.5rem 1.5rem; font-weight: 600;
    transition: all 0.2s;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(49,130,206,0.4); }
div[data-testid="metric-container"] {
    background: #1a2035; border-radius: 10px;
    padding: 15px; border: 1px solid rgba(255,255,255,0.1);
}
</style>
""", unsafe_allow_html=True)

# ── Session State ────────────────────────────────────────────────────────────
for key, val in {
    "token": None, "user": None, "page": "login",
    "resume_id": None, "parsed_data": None, "analysis_result": None,
    "jd_id": None, "history": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── API Helpers ──────────────────────────────────────────────────────────────
def auth_headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


def api(method, endpoint, **kwargs):
    try:
        resp = requests.request(
            method, f"{API_BASE}/{endpoint}",
            headers=auth_headers(), timeout=120, **kwargs
        )
        if resp.status_code in (200, 201):
            return resp.json(), None
        try:
            err = resp.json().get("detail", resp.text)
        except Exception:
            err = resp.text
        return None, err
    except requests.exceptions.ConnectionError:
        return None, "❌ Cannot connect to backend. Is FastAPI running on port 8000?"
    except Exception as e:
        return None, str(e)


def score_class(s):
    if s >= 75: return "score-excellent"
    if s >= 50: return "score-good"
    return "score-low"


def score_emoji(s):
    if s >= 75: return "🟢"
    if s >= 50: return "🟡"
    return "🔴"


# ── Auth Check ────────────────────────────────────────────────────────────────
def require_auth():
    if not st.session_state.token:
        st.warning("⚠️ Please log in first.")
        st.session_state.page = "login"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════════════════════

def page_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 🧠 AI Resume Intelligence")
        st.markdown("#### Sign in to your account")
        st.markdown("---")
        email = st.text_input("Email", placeholder="you@example.com", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔑 Sign In", use_container_width=True, type="primary"):
                if email and password:
                    data, err = api("POST", "auth/login", data={"username": email, "password": password})
                    if data:
                        st.session_state.token = data["access_token"]
                        st.session_state.user = data["user"]
                        st.session_state.page = "dashboard"
                        st.success("✅ Logged in!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Login failed: {err}")
                else:
                    st.warning("Enter email and password.")
        with col_b:
            if st.button("📝 Register", use_container_width=True):
                st.session_state.page = "register"
                st.rerun()


def page_register():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 🧠 Create Account")
        st.markdown("---")
        name = st.text_input("Full Name", key="reg_name")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password (min 8 chars)", type="password", key="reg_pass")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Register", use_container_width=True, type="primary"):
                if name and email and password:
                    data, err = api("POST", "auth/register", json={"name": name, "email": email, "password": password})
                    if data:
                        st.success("✅ Account created! Please log in.")
                        time.sleep(1)
                        st.session_state.page = "login"
                        st.rerun()
                    else:
                        st.error(f"Registration failed: {err}")
                else:
                    st.warning("Fill in all fields.")
        with col_b:
            if st.button("← Back to Login", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()


def page_dashboard():
    require_auth()
    user = st.session_state.user or {}
    st.markdown(f"## 🏠 Dashboard")
    st.markdown(f"Welcome back, **{user.get('name', 'User')}**! 👋")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card"><h3>📄</h3><p>Resume</p><h2 style="color:#90cdf4">{}</h2></div>'.format(
            "Uploaded" if st.session_state.resume_id else "Not uploaded"), unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card"><h3>🚀</h3><p>Analyses Run</p><h2 style="color:#90cdf4">{}</h2></div>'.format(
            len(st.session_state.history)), unsafe_allow_html=True)
    with col3:
        score = None
        if st.session_state.analysis_result:
            score = st.session_state.analysis_result.get("ats_score", {}).get("total_score")
        st.markdown('<div class="metric-card"><h3>🎯</h3><p>Latest ATS</p><h2 class="{}">{}</h2></div>'.format(
            score_class(score or 0), f"{score:.0f}" if score else "—"), unsafe_allow_html=True)
    with col4:
        sim = None
        if st.session_state.analysis_result:
            sim = st.session_state.analysis_result.get("match_result", {}).get("similarity_percentage")
        st.markdown('<div class="metric-card"><h3>🔍</h3><p>Latest Match</p><h2 class="{}">{}</h2></div>'.format(
            score_class(sim or 0), f"{sim:.0f}%" if sim else "—"), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Quick Actions")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("📤 Upload Resume", use_container_width=True):
            st.session_state.page = "upload"; st.rerun()
    with c2:
        if st.button("📋 Upload JD", use_container_width=True):
            st.session_state.page = "upload_jd"; st.rerun()
    with c3:
        if st.button("🚀 Analyze", use_container_width=True):
            st.session_state.page = "analyze"; st.rerun()
    with c4:
        if st.button("📊 History", use_container_width=True):
            st.session_state.page = "history"; st.rerun()


def page_upload():
    require_auth()
    st.markdown("## 📤 Upload Resume")
    st.markdown("Supported formats: **PDF, DOCX, TXT** | Max size: **10MB**")
    st.markdown("---")

    uploaded = st.file_uploader("Choose your resume file", type=["pdf", "docx", "txt"])
    if uploaded:
        st.info(f"📄 File selected: **{uploaded.name}** ({len(uploaded.getvalue())//1024}KB)")
        if st.button("📤 Upload & Parse", type="primary", use_container_width=True):
            with st.spinner("Parsing resume..."):
                files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
                data, err = api("POST", "upload", files=files)
            if data:
                st.session_state.resume_id = data["resume_id"]
                st.session_state.parsed_data = data["parsed_data"]
                st.session_state.analysis_result = None
                st.success(f"✅ Resume uploaded! ID: `{str(data['resume_id'])[:8]}…`")

    if st.session_state.parsed_data:
        pd = st.session_state.parsed_data
        st.markdown("### 📋 Parsed Resume Data")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**👤 Name:** {pd.get('name') or 'Not detected'}")
            st.markdown(f"**📧 Email:** {pd.get('email') or 'Not detected'}")
            st.markdown(f"**📞 Phone:** {pd.get('phone') or 'Not detected'}")
        with c2:
            skills = pd.get("skills", [])
            st.markdown(f"**🛠 Skills ({len(skills)}):**")
            if skills:
                st.markdown(" ".join(f'<span class="tag">{s}</span>' for s in skills[:20]), unsafe_allow_html=True)

        if pd.get("raw_text"):
            with st.expander("📄 Raw Extracted Text"):
                st.text_area("", pd["raw_text"][:3000], height=200, disabled=True)


def page_upload_jd():
    require_auth()
    st.markdown("## 📋 Upload Job Description")
    st.markdown("---")
    title = st.text_input("Job Title", placeholder="Senior Software Engineer")
    company = st.text_input("Company (optional)", placeholder="Google, Meta, ...")
    description = st.text_area("Paste Full Job Description", height=300,
        placeholder="We are looking for a Senior Software Engineer with 5+ years experience in Python, FastAPI, PostgreSQL...")
    if st.button("💾 Save Job Description", type="primary", use_container_width=True):
        if title and description and len(description) >= 50:
            data, err = api("POST", "upload/job-description",
                json={"title": title, "company": company or None, "description": description})
            if data:
                st.session_state.jd_id = data["id"]
                st.success(f"✅ JD saved! ID: `{str(data['id'])[:8]}…`")
            else:
                st.error(f"Failed: {err}")
        else:
            st.warning("Title and description (min 50 chars) are required.")


def page_analyze():
    require_auth()
    st.markdown("## 🚀 Resume Analysis")
    st.markdown("---")

    if not st.session_state.resume_id:
        st.warning("⚠️ Upload a resume first.")
        if st.button("📤 Go to Upload"): st.session_state.page = "upload"; st.rerun()
        return

    st.success(f"✅ Resume ready: `{str(st.session_state.resume_id)[:8]}…`")
    job_description = st.text_area("Paste Job Description", height=200,
        placeholder="Paste the full job description here...")
    job_title = st.text_input("Job Title (optional)")
    company = st.text_input("Company (optional)")

    c1, c2, c3 = st.columns(3)
    with c1: run_full = st.button("🚀 Full Analysis", type="primary", use_container_width=True)
    with c2: run_ats = st.button("🎯 ATS Only", use_container_width=True)
    with c3: run_match = st.button("🔍 Match Only", use_container_width=True)

    if (run_full or run_ats or run_match) and not job_description.strip():
        st.warning("⚠️ Paste a job description first.")
        return

    if run_full:
        with st.spinner("🤖 Running full AI pipeline (30-90s)…"):
            payload = {"resume_id": str(st.session_state.resume_id),
                       "job_description": job_description,
                       "job_title": job_title or None,
                       "company": company or None}
            data, err = api("POST", "analyze", json=payload)
        if data:
            st.session_state.analysis_result = data
            st.success("✅ Analysis complete!")
        else:
            st.error(f"Analysis failed: {err}")

    if run_ats:
        with st.spinner("🎯 Calculating ATS score…"):
            data, err = api("POST", "ats-score",
                json={"resume_id": str(st.session_state.resume_id), "job_description": job_description})
        if data:
            st.markdown("### 🎯 ATS Score")
            total = data.get("total_score", 0)
            st.markdown(f'<p class="{score_class(total)}">{score_emoji(total)} {total:.1f} / 100</p>', unsafe_allow_html=True)
            st.progress(min(total / 100, 1.0))
            for label, key, mx in [("Keywords", "keyword_score", 25), ("Skills", "skills_score", 20),
                                     ("Experience", "experience_score", 15), ("Education", "education_score", 10)]:
                v = data.get(key, 0)
                st.markdown(f"**{label}:** {v:.1f}/{mx}")
                st.progress(v / mx if mx else 0)
        elif err:
            st.error(f"ATS failed: {err}")

    if run_match:
        with st.spinner("🔍 Computing semantic similarity…"):
            data, err = api("POST", "match",
                json={"resume_id": str(st.session_state.resume_id),
                      "job_description": job_description, "resume_skills": []})
        if data:
            st.markdown("### 🔍 Semantic Match")
            sim = data.get("similarity_percentage", 0)
            st.markdown(f'<p class="{score_class(sim)}">{score_emoji(sim)} {sim:.1f}% Match</p>', unsafe_allow_html=True)
            st.info(data.get("match_verdict", ""))
        elif err:
            st.error(f"Match failed: {err}")

    # ── Show full analysis result ─────────────────────────────────────────────
    if st.session_state.analysis_result:
        res = st.session_state.analysis_result
        st.markdown("---")
        st.markdown("## 📊 Analysis Results")

        ats = res.get("ats_score", {})
        match = res.get("match_result", {})
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🎯 ATS Score")
            total = ats.get("total_score", 0)
            st.markdown(f'<div class="metric-card"><p class="{score_class(total)}">{score_emoji(total)} {total:.1f}/100</p></div>', unsafe_allow_html=True)
            for label, key, mx in [("Keywords", "keyword_score", 25), ("Skills", "skills_score", 20),
                                     ("Experience", "experience_score", 15), ("Formatting", "format_score", 10)]:
                v = ats.get(key, 0)
                st.markdown(f"**{label}:** {v:.1f}/{mx}")
                st.progress(v / mx if mx else 0)
        with c2:
            st.markdown("### 🔍 Semantic Match")
            sim = match.get("similarity_percentage", 0)
            st.markdown(f'<div class="metric-card"><p class="{score_class(sim)}">{score_emoji(sim)} {sim:.1f}%</p></div>', unsafe_allow_html=True)
            st.info(match.get("match_verdict", ""))
            matching = match.get("matching_skills", [])
            if matching:
                st.markdown("**✅ Matching Skills:**")
                st.markdown(" ".join(f'<span class="tag">{s}</span>' for s in matching[:15]), unsafe_allow_html=True)
            missing = match.get("missing_skills", [])
            if missing:
                st.markdown("**❌ Missing Skills:**")
                st.markdown(" ".join(f'<span class="tag tag-missing">{s}</span>' for s in missing[:15]), unsafe_allow_html=True)

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["💡 AI Insights", "🎯 Improvements", "📋 Feedback", "🔑 Keywords", "📈 Skill Gap"])

        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**💪 Strengths**")
                for s in res.get("strengths", []): st.markdown(f"✅ {s}")
            with c2:
                st.markdown("**⚠️ Weaknesses**")
                for w in res.get("weaknesses", []): st.markdown(f"⚠️ {w}")
            st.markdown("**📖 Career Advice**")
            st.info(res.get("career_advice", ""))
            st.markdown("**🎤 Interview Tips**")
            for t in res.get("interview_tips", []): st.markdown(f"• {t}")
            st.markdown("**📈 Career Roadmap**")
            for i, s in enumerate(res.get("career_roadmap", []), 1): st.markdown(f"**Step {i}:** {s}")

        with tab2:
            imp = res.get("improve_result", {})
            for b in imp.get("improved_bullets", []):
                st.markdown(f"**Original:** {b.get('original','')}")
                st.success(f"**Improved:** {b.get('improved','')}")
                st.caption(f"_{b.get('explanation','')}_")
                st.markdown("---")
            st.markdown("**General Tips:**")
            for s in imp.get("overall_suggestions", []): st.markdown(f"• {s}")

        with tab3:
            for sec in res.get("feedback", {}).get("sections", []):
                with st.expander(f"**{sec.get('section','')}** — {sec.get('score',0):.1f}/10"):
                    st.markdown(sec.get("feedback", ""))
                    for sug in sec.get("suggestions", []): st.markdown(f"• {sug}")
            st.markdown("**Overall Verdict:**")
            st.markdown(res.get("feedback", {}).get("overall_verdict", ""))

        with tab4:
            kw = res.get("keyword_result", {})
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Missing ATS Keywords:**")
                for k in kw.get("missing_ats_keywords", []): st.markdown(f"• `{k}`")
                st.markdown("**Industry Terms:**")
                for k in kw.get("industry_terms", []): st.markdown(f"• `{k}`")
            with c2:
                st.markdown("**Action Verbs:**")
                for k in kw.get("action_verbs", []): st.markdown(f"• `{k}`")
                st.markdown("**Modern Technologies:**")
                for k in kw.get("modern_technologies", []): st.markdown(f"• `{k}`")

        with tab5:
            gap = res.get("skill_gap", {})
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("🔴 **High Priority**")
                for s in gap.get("high_priority_missing", []): st.markdown(f"• {s}")
            with c2:
                st.markdown("🟡 **Medium Priority**")
                for s in gap.get("medium_priority_missing", []): st.markdown(f"• {s}")
            with c3:
                st.markdown("🔵 **Future Skills**")
                for s in gap.get("future_skills", []): st.markdown(f"• {s}")
            for item in gap.get("learning_roadmap", []):
                st.markdown(f"• **{item.get('skill','')}** — {item.get('resource','')} | ⏱️ {item.get('timeline','')} | 🔺 {item.get('priority','')}")

        st.markdown("---")
        if res.get("analysis_id"):
            analysis_id = res["analysis_id"]
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇️ Download JSON Report", json.dumps(res, indent=2),
                    file_name="resume_report.json", mime="application/json", use_container_width=True)
            with c2:
                if st.button("📄 Download PDF Report", use_container_width=True):
                    pdf_data, err = api("GET", f"reports/{analysis_id}/download")
                    if err:
                        st.error(f"PDF generation failed: {err}")


def page_history():
    require_auth()
    st.markdown("## 📊 Analysis History")
    st.markdown("---")
    with st.spinner("Loading history…"):
        data, err = api("GET", "history")
    if err:
        st.error(f"Failed: {err}"); return
    if not data:
        st.info("No analyses yet. Upload a resume and run an analysis!"); return
    for item in data:
        ats = item.get("ats_score") or 0
        sim = item.get("similarity_score") or 0
        status = item.get("status", "unknown")
        status_icon = "✅" if status == "completed" else "❌" if status == "failed" else "⏳"
        with st.expander(f"{status_icon} {item.get('resume_filename','resume')} — {item.get('job_title') or 'No title'} | ATS: {ats:.0f} | Match: {sim:.0f}%"):
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("ATS Score", f"{ats:.1f}/100")
            with c2: st.metric("Semantic Match", f"{sim:.1f}%")
            with c3: st.metric("Status", status.title())
            analysis_id = item.get("analysis_id")
            if analysis_id and status == "completed":
                if st.button(f"📑 View Report", key=f"view_{analysis_id}"):
                    report, err2 = api("GET", f"reports/{analysis_id}")
                    if report:
                        st.json(report)
                    elif err2:
                        st.error(err2)


def page_profile():
    require_auth()
    st.markdown("## 👤 Profile")
    st.markdown("---")
    data, err = api("GET", "auth/me")
    if data:
        st.markdown(f"**Name:** {data.get('name')}")
        st.markdown(f"**Email:** {data.get('email')}")
        st.markdown(f"**Member Since:** {data.get('created_at','')[:10]}")
        st.markdown(f"**Status:** {'✅ Active' if data.get('is_active') else '❌ Inactive'}")
    else:
        st.error(f"Failed to load profile: {err}")


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.token:
    with st.sidebar:
        user = st.session_state.user or {}
        st.markdown(f"### 🧠 Resume Intelligence")
        st.markdown(f"👤 **{user.get('name','User')}**")
        st.markdown("---")
        pages = [
            ("🏠 Dashboard", "dashboard"),
            ("📤 Upload Resume", "upload"),
            ("📋 Upload JD", "upload_jd"),
            ("🚀 Analyze", "analyze"),
            ("📊 History", "history"),
            ("👤 Profile", "profile"),
        ]
        for label, page_key in pages:
            if st.button(label, use_container_width=True, key=f"nav_{page_key}"):
                st.session_state.page = page_key
                st.rerun()
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            api("POST", "auth/logout")
            for k in ["token", "user", "resume_id", "parsed_data", "analysis_result", "jd_id", "history"]:
                st.session_state[k] = None if k != "history" else []
            st.session_state.page = "login"
            st.rerun()
        st.markdown("---")
        st.markdown("**🔗 Links**")
        st.markdown("[📖 API Docs](http://localhost:8000/docs)")
        st.markdown("[❤️ Health Check](http://localhost:8000/api/v1/health)")

# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
page_map = {
    "login": page_login,
    "register": page_register,
    "dashboard": page_dashboard,
    "upload": page_upload,
    "upload_jd": page_upload_jd,
    "analyze": page_analyze,
    "history": page_history,
    "profile": page_profile,
}

current = st.session_state.page
if current not in page_map:
    current = "login"
page_map[current]()
