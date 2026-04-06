import streamlit as st
import os
import re
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from parser import extract_text
from ai_engine import extract_profile, generate_summary
from scorer import calculate_score

st.set_page_config(
    page_title="Smart Talent Engine",
    layout="wide",
    page_icon="💼"
)

st.markdown("""
<style>
    .candidate-card {
        padding: 18px 22px;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        margin-bottom: 14px;
        background: #fafafa;
    }
    .score-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.95em;
    }
    .score-high  { background: #d4edda; color: #155724; }
    .score-mid   { background: #fff3cd; color: #856404; }
    .score-low   { background: #f8d7da; color: #721c24; }
    .breakdown-row { font-size: 0.85em; color: #555; margin-top: 6px; }
    .tag { display:inline-block; padding:2px 8px; border-radius:12px;
           background:#e8f0fe; color:#1a56db; font-size:0.78em; margin:2px; }
    .error-box { padding:8px 14px; border-radius:8px;
                 background:#fff3f3; border:1px solid #fcc; margin:4px 0; font-size:0.88em; }
    .warn-box  { padding:8px 14px; border-radius:8px;
                 background:#fffbe6; border:1px solid #ffe58f; margin:4px 0; font-size:0.88em; }
</style>
""", unsafe_allow_html=True)

def score_class(score: float) -> str:
    if score >= 70:
        return "score-high"
    elif score >= 45:
        return "score-mid"
    return "score-low"

def mini_bar(value: float, color: str = "#4a90e2") -> str:
    pct = min(max(value, 0), 100)
    return (
        f'<div style="background:#eee;border-radius:4px;height:7px;width:100%;margin-top:3px;">'
        f'<div style="background:{color};width:{pct}%;height:7px;border-radius:4px;"></div></div>'
    )

def format_skills(skills) -> str:
    if not isinstance(skills, list):
        return "—"
    return "".join(f'<span class="tag">{sanitize(s)}</span>' for s in skills[:12])

def sanitize(text) -> str:
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace('"', "")
    text = text.replace("'", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def process_single_resume(file_path: str, file_name: str, jd_text: str, job_role: str) -> dict:
    """
    Runs inside a worker thread. Handles text extraction, profile extraction,
    and scoring for one resume. Returns a result dict with either a candidate
    record or an error/warning entry. Never touches Streamlit state.
    """
    try:
        text, status = extract_text(file_path)

        if not status["valid"]:
            reason = status["reason"]
            if reason == "unsupported_format":
                return {"type": "error", "file_name": file_name, "reason": "Unsupported file format."}
            elif reason == "empty":
                return {"type": "warning", "file_name": file_name, "reason": "File is empty or contains no extractable text."}
            elif reason.startswith("corrupt"):
                return {"type": "error", "file_name": file_name, "reason": f"File appears corrupt or unreadable. ({reason})"}
            else:
                return {"type": "error", "file_name": file_name, "reason": reason}

        profile = extract_profile(text)
        breakdown = calculate_score(text, jd_text)

        profile.update({
            "file_name": file_name,
            "job_role": job_role or "Untagged",
            "batch_date": datetime.now().strftime("%Y-%m-%d"),
            "score": breakdown["final"],
            "semantic_score": breakdown["semantic"],
            "skill_score": breakdown["skill"],
            "experience_score": breakdown["experience"],
            "exp_years": breakdown["exp_years"],
            "keyword_stuffing": breakdown.get("keyword_stuffing", {}),
            "summary": ""
        })

        return {"type": "success", "file_name": file_name, "candidate": profile}

    except Exception as e:
        return {"type": "error", "file_name": file_name, "reason": str(e)}

with st.sidebar:
    st.header("⚙️ Filters & Settings")

    job_role = st.text_input(
        "🏷️ Job Role / Batch Label",
        placeholder="e.g. Backend Engineer – Batch Apr 2025",
        help="Tag this upload session for easy reference."
    )

    st.markdown("---")
    st.subheader("Filter Results")
    min_score = st.slider("Minimum Compatibility Score (%)", 0, 100, 0)

    st.markdown("---")
    st.subheader("⚡ Performance")
    max_workers = st.slider(
        "Parallel Workers",
        min_value=1,
        max_value=6,
        value=3,
        help=(
            "How many resumes to process at the same time.\n\n"
            "• 1–2 workers → safest, lowest RAM (~50–100 MB extra)\n"
            "• 3 workers → good balance (recommended)\n"
            "• 4–6 workers → fastest, needs 8 GB+ RAM\n\n"
            "Ollama LLM calls are always sequential regardless of this setting."
        )
    )

    st.markdown("---")
    st.caption("Smart Talent Engine v2.1")

st.title("💼 Smart Talent Engine")
st.caption("AI-powered Resume Screening & Ranking System")

if job_role:
    batch_time = datetime.now().strftime("%d %b %Y, %H:%M")
    st.info(f"📁 **Batch:** {job_role}  ·  {batch_time}", icon="🗂️")

st.markdown("---")

st.subheader("📌 Job Description")

jd_input_method = st.radio(
    "How do you want to provide the JD?",
    ["Type / Paste", "Upload File (PDF or DOCX)"],
    horizontal=True
)

jd_text = ""

if jd_input_method == "Type / Paste":
    jd_text = st.text_area(
        "Paste the full job description here",
        height=180,
        placeholder="Include required skills, responsibilities, and experience level..."
    )

else:
    jd_file = st.file_uploader(
        "Upload JD file",
        type=["pdf", "docx"],
        key="jd_uploader"
    )

    if jd_file:
        os.makedirs("jd_uploads", exist_ok=True)
        jd_path = os.path.join("jd_uploads", "uploaded_jd_" + jd_file.name)

        with open(jd_path, "wb") as f:
            f.write(jd_file.getbuffer())

        jd_text, jd_status = extract_text(jd_path)

        if jd_status["valid"]:
            st.success(f"✅ JD loaded from **{jd_file.name}**")
            with st.expander("Preview extracted JD text"):
                st.text(jd_text[:1000] + "..." if len(jd_text) > 1000 else jd_text)
        else:
            st.error(f"❌ Could not read JD file: {jd_status['reason']}")
            jd_text = ""

st.markdown("---")
st.subheader("📤 Upload Resumes")
st.caption("Accepted formats: PDF, DOCX, JPG, PNG")
uploaded_files = st.file_uploader(
    "Drop files here or click Browse",
    accept_multiple_files=True,
    type=["pdf", "docx", "jpg", "jpeg", "png"],
    label_visibility="collapsed"
)

if uploaded_files:
    st.caption(f"**{len(uploaded_files)} file(s) selected.**")

st.markdown("---")

if st.button("🚀 Screen Resumes", use_container_width=True):

    if not jd_text.strip():
        st.warning("⚠️ Please provide a Job Description before processing.")
        st.stop()

    if not uploaded_files:
        st.warning("⚠️ Please upload at least one resume.")
        st.stop()

    os.makedirs("resumes", exist_ok=True)

    saved_files = []
    for file in uploaded_files:
        file_path = os.path.join("resumes", file.name)
        try:
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
            saved_files.append((file_path, file.name))
        except Exception as e:
            st.warning(f"⚠️ Could not save **{file.name}**: {e}")

    if not saved_files:
        st.error("No files could be saved. Please try again.")
        st.stop()

    total = len(saved_files)
    all_candidates = []
    file_errors = []
    file_warnings = []

    completed_count = 0

    progress_bar = st.progress(0, text=f"Processing 0 / {total}…")
    status_text = st.empty()

    if max_workers > 1:
        status_text.markdown(
            f"⚡ Running with **{max_workers} parallel workers** — "
            f"progress updates as each resume finishes."
        )
    else:
        status_text.markdown("⏳ Processing resumes one at a time…")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        futures_map = {
            executor.submit(
                process_single_resume,
                file_path,
                file_name,
                jd_text,
                job_role
            ): file_name
            for file_path, file_name in saved_files
        }

        for future in as_completed(futures_map):
            file_name = futures_map[future]
            completed_count += 1

            pct = int((completed_count / total) * 100)
            progress_bar.progress(
                pct,
                text=f"Processed {completed_count} / {total} — last finished: {file_name}"
            )

            try:
                result = future.result()
            except Exception as e:
                file_errors.append((file_name, str(e)))
                continue

            if result["type"] == "success":
                all_candidates.append(result["candidate"])
            elif result["type"] == "warning":
                file_warnings.append((result["file_name"], result["reason"]))
            else:
                file_errors.append((result["file_name"], result["reason"]))

    progress_bar.progress(100, text=f"Done — {total} file(s) processed ✅")
    status_text.empty()

    if file_errors:
        with st.expander(f"❌ {len(file_errors)} file(s) could not be processed", expanded=True):
            for fname, reason in file_errors:
                st.markdown(
                    f'<div class="error-box">❌ <b>{fname}</b> — {reason}</div>',
                    unsafe_allow_html=True
                )

    if file_warnings:
        with st.expander(f"⚠️ {len(file_warnings)} file(s) had warnings"):
            for fname, msg in file_warnings:
                st.markdown(
                    f'<div class="warn-box">⚠️ <b>{fname}</b> — {msg}</div>',
                    unsafe_allow_html=True
                )

    if not all_candidates:
        st.error("No valid resumes were processed. Please check the files and try again.")
        st.stop()

    df = pd.DataFrame(all_candidates)
    df = df.sort_values(by="score", ascending=False).reset_index(drop=True)
    df = df[df["score"] >= min_score]

    if df.empty:
        st.warning("No candidates match the current filters.")
        st.stop()

    top5_indices = df.head(5).index.tolist()
    summary_status = st.empty()

    for i, row_idx in enumerate(top5_indices):
        summary_status.markdown(
            f"✍️ Generating AI summary for candidate {i+1} of {min(5, len(top5_indices))}…"
        )
        row = df.loc[row_idx]
        breakdown = {
            "semantic": row["semantic_score"],
            "skill": row["skill_score"],
            "experience": row["experience_score"],
            "final": row["score"]
        }
        summary = generate_summary(
            profile={
                "skills": row["skills"],
                "experience": row["experience"],
                "education": row["education"]
            },
            jd_text=jd_text,
            score_breakdown=breakdown
        )
        df.at[row_idx, "summary"] = summary

    summary_status.empty()

    st.success(f"✅ {len(df)} candidate(s) ranked successfully.")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Candidates", len(df))
    col2.metric("Top Score", f"{df['score'].max():.1f}%")
    col3.metric("Average Score", f"{df['score'].mean():.1f}%")
    col4.metric("Avg. Experience", f"{df['exp_years'].mean():.1f} yrs")

    if job_role:
        st.markdown(
            f'<div style="margin:8px 0;font-size:0.88em;color:#666;">'
            f'📁 Batch: <b>{job_role}</b> &nbsp;·&nbsp; '
            f'Date: <b>{df["batch_date"].iloc[0]}</b>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.subheader("🏆 Top Candidates")

    for rank, (_, row) in enumerate(df.head(5).iterrows(), start=1):
        skills = row["skills"] if isinstance(row["skills"], list) else []
        sc = score_class(row["score"])

        safe_summary = sanitize(row["summary"])
        safe_experience = sanitize(row["experience"])
        safe_education = sanitize(row["education"])
        safe_filename = sanitize(row["file_name"])

        candidate_name = sanitize(row.get("name", ""))
        display_name = candidate_name if candidate_name and candidate_name != "Unknown" else safe_filename

        summary_html = (
            f'<p style="margin:8px 0 0 0;font-size:0.9em;color:#333;">'
            f'<b>AI Summary:</b> {safe_summary}</p>'
        ) if safe_summary else ""

        ks = row.get("keyword_stuffing", {})
        if isinstance(ks, dict) and ks.get("flagged"):
            stuffing_html = (
                f'<div style="margin:8px 0 4px 0;padding:6px 12px;'
                f'background:#fff3cd;border-left:3px solid #f0ad4e;'
                f'border-radius:4px;font-size:0.82em;color:#856404;">'
                f'⚠️ <b>Keyword Stuffing Suspected:</b> '
                f'{sanitize(ks.get("message", ""))}</div>'
            )
        else:
            stuffing_html = ""

        filename_sub = (
            f'<span style="font-size:0.78em;color:#888;font-weight:400;margin-left:8px;">'
            f'{safe_filename}</span>'
        ) if display_name != safe_filename else ""

        st.markdown(f"""
        <div class="candidate-card">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <h4 style="margin:0;">#{rank} &nbsp; {display_name}{filename_sub}</h4>
            <span class="score-badge {sc}">{row['score']:.1f}%</span>
          </div>

          <div class="breakdown-row">
            <b>Semantic Alignment</b> {row['semantic_score']:.0f}%
            {mini_bar(row['semantic_score'], '#4a90e2')}
          </div>
          <div class="breakdown-row">
            <b>Skill Match</b> {row['skill_score']:.0f}%
            {mini_bar(row['skill_score'], '#27ae60')}
          </div>
          <div class="breakdown-row">
            <b>Experience Depth</b> {row['experience_score']:.0f}%
            &nbsp;<span style="color:#888;">({row['exp_years']} yrs detected)</span>
            {mini_bar(row['experience_score'], '#e67e22')}
          </div>

          <p style="margin:10px 0 4px 0;">
            <b>Skills:</b> {format_skills(skills)}
          </p>
          <p style="margin:4px 0;font-size:0.88em;color:#444;">
            <b>Experience:</b> {safe_experience}
          </p>
          <p style="margin:4px 0;font-size:0.88em;color:#444;">
            <b>Education:</b> {safe_education}
          </p>
          {stuffing_html}
          {summary_html}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 All Candidates")

    display_cols = [
        "name", "file_name", "job_role", "batch_date", "score",
        "semantic_score", "skill_score", "experience_score",
        "exp_years", "experience", "education"
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df[display_cols].rename(columns={
            "name": "Candidate",
            "file_name": "Resume",
            "job_role": "Job Role",
            "batch_date": "Batch Date",
            "score": "Score (%)",
            "semantic_score": "Semantic (%)",
            "skill_score": "Skill (%)",
            "experience_score": "Exp. Score (%)",
            "exp_years": "Years Exp.",
            "experience": "Experience Summary",
            "education": "Education"
        }),
        use_container_width=True,
        height=400
    )

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Full Results (CSV)",
        data=csv,
        file_name=f"talent_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True
    )
