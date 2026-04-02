import streamlit as st
import os
import pandas as pd

from parser import extract_text
from ai_engine import extract_profile, call_gemini
from scorer import calculate_score

st.set_page_config(page_title="Smart Talent Engine", layout="wide")

st.title("💼 Smart Talent Engine")
st.caption("AI-powered Resume Screening & Ranking System")

st.sidebar.header("⚙️ Filters")
min_score = st.sidebar.slider("Minimum Score", 0, 100, 0)
selected_skill = st.sidebar.text_input("Filter by Skill (optional)")

jd_text = st.text_area("📌 Enter Job Description", height=150)

uploaded_files = st.file_uploader("📤 Upload Resumes", accept_multiple_files=True)

def generate_summary(profile, jd_text):
    prompt = f"""
    Job Description:
    {jd_text}

    Candidate:
    Skills: {profile.get("skills")}
    Experience: {profile.get("experience")}

    Write a professional 2 sentence evaluation.
    """

    try:
        return call_gemini(prompt)
    except:
        return "Summary not available"

if st.button("🚀 Process Resumes"):

    if not jd_text:
        st.warning("Enter Job Description")
    elif not uploaded_files:
        st.warning("Upload resumes")
    else:
        all_candidates = []

        with st.spinner("Processing resumes... ⏳"):
            for file in uploaded_files:
                try:
                    file_path = os.path.join("resumes", file.name)

                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer())

                    text = extract_text(file_path)

                    if not text.strip():
                        continue

                    profile = extract_profile(text)
                    score = calculate_score(text, jd_text)

                    summary = generate_summary(profile, jd_text)

                    profile.update({
                        "file_name": file.name,
                        "score": score,
                        "summary": summary
                    })

                    all_candidates.append(profile)

                except Exception as e:
                    st.error(f"{file.name} error: {e}")

        if all_candidates:
            df = pd.DataFrame(all_candidates)
            df = df.sort_values(by="score", ascending=False)

            df = df[df["score"] >= min_score]

            if selected_skill:
                df = df[df["skills"].apply(
                    lambda x: selected_skill.lower() in " ".join(x).lower()
                )]

            st.success("✅ Processing Complete")

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Candidates", len(df))
            col2.metric("Top Score", f"{df['score'].max()} %")
            col3.metric("Average Score", f"{round(df['score'].mean(), 2)} %")

            st.divider()

            st.subheader("🏆 Top Candidates")
            top = df.head(5)

            for _, row in top.iterrows():
                skills = row['skills'] if isinstance(row['skills'], list) else []

                st.markdown(f"""
                <div style="
                    padding:15px;
                    border-radius:10px;
                    border:1px solid #ddd;
                    margin-bottom:10px;">

                <h4>{row['file_name']}</h4>

                <b>Score:</b> {row['score']}% <br>
                <b>Skills:</b> {', '.join(skills)} <br>
                <b>Experience:</b> {row['experience']} <br>
                <b>Summary:</b> {row['summary']}

                </div>
                """, unsafe_allow_html=True)

            st.divider()

            st.subheader("📋 All Candidates")
            st.dataframe(df)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download CSV", csv, "results.csv")

        else:
            st.warning("No valid resumes processed")