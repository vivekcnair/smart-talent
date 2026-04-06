import requests
import json
import re

# ─────────────────────────────────────────────
# OLLAMA / LLAMA SETUP
# ─────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"


# ─────────────────────────────────────────────
# CORE LLAMA CALLER
# ─────────────────────────────────────────────
def call_llama(prompt: str) -> str:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            }
        )

        if response.status_code != 200:
            print("LLAMA ERROR:", response.text)
            return ""

        return response.json().get("response", "")

    except Exception as e:
        print(f"Request Error: {e}")
        return ""


# ─────────────────────────────────────────────
# ROBUST JSON EXTRACTOR
# ─────────────────────────────────────────────
def extract_json(text: str) -> dict:
    """
    Extracts the first valid JSON object from a text block.
    Handles markdown code fences, trailing commas, and minor formatting issues.
    """
    try:
        # Strip markdown fences if present
        text = re.sub(r"```(?:json)?", "", text).strip()

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            json_str = match.group()
            # Fix trailing commas
            json_str = re.sub(r",\s*}", "}", json_str)
            json_str = re.sub(r",\s*]", "]", json_str)
            return json.loads(json_str)

    except Exception as e:
        print(f"JSON Parse Error: {e}")

    return {}


# ─────────────────────────────────────────────
# RESUME PROFILE EXTRACTOR
# ─────────────────────────────────────────────
def extract_profile(text: str) -> dict:
    prompt = f"""
You are an AI resume parser.

Extract:
- skills (list)
- experience (short summary)
- education

Return ONLY JSON:
{{
  "skills": [],
  "experience": "",
  "education": ""
}}

Resume:
{text[:3000]}
"""

    content = call_llama(prompt)
    print("RAW:", content)

    data = extract_json(content)

    # ── Skills normalisation ──
    skills = data.get("skills", [])
    if isinstance(skills, str):
        skills = [s.strip() for s in re.split(r"[,;]", skills) if s.strip()]
    skills = [s for s in skills if isinstance(s, str) and s.strip()]

    # ── Education normalisation ──
    education = data.get("education", "")
    if isinstance(education, list):
        parts = []
        for edu in education:
            if isinstance(edu, dict):
                parts.append(
                    f"{edu.get('degree', '')} - {edu.get('institution', '')} ({edu.get('year', '')})"
                )
            else:
                parts.append(str(edu))
        education = " | ".join(parts)
    elif isinstance(education, dict):
        education = f"{education.get('degree', '')} - {education.get('institution', '')} ({education.get('year', '')})"

    return {
        "skills": skills,
        "experience": data.get("experience", "Not found"),
        "education": education or "Not found"
    }


# ─────────────────────────────────────────────
# LLM-BASED SKILL EXTRACTOR (used by scorer)
# ─────────────────────────────────────────────
def extract_skills_llm(text: str) -> list:
    prompt = f"""
Extract ONLY technical skills as a JSON list.

Text:
{text[:2000]}
"""

    response = call_llama(prompt)

    try:
        response = re.sub(r"```(?:json)?", "", response).strip()
        result = json.loads(response)
        if isinstance(result, list):
            return [s.lower() for s in result if isinstance(s, str)]
    except Exception:
        pass

    return []


# ─────────────────────────────────────────────
# SUMMARY OF FIT — TOP CANDIDATES ONLY
# ─────────────────────────────────────────────
def generate_summary(profile: dict, jd_text: str, score_breakdown: dict = None) -> str:
    """
    Generates a 2-sentence Summary of Fit for a candidate.

    score_breakdown (optional): {
        "semantic": float,
        "skill": float,
        "experience": float,
        "final": float
    }

    When provided, the prompt references the breakdown so the summary
    explicitly explains WHY the candidate ranked highly.
    """

    breakdown_hint = ""
    if score_breakdown:
        breakdown_hint = f"""
Score Breakdown (use these to justify your evaluation):
- Semantic alignment with JD: {round(score_breakdown.get('semantic', 0), 1)}%
- Skill match: {round(score_breakdown.get('skill', 0), 1)}%
- Experience depth: {round(score_breakdown.get('experience', 0), 1)}%
- Overall compatibility: {round(score_breakdown.get('final', 0), 1)}%
"""

    prompt = f"""
Job Description:
{jd_text[:800]}

Candidate:
Skills: {', '.join(profile.get('skills', [])) or 'Not listed'}
Experience: {profile.get('experience', 'Not found')}
Education: {profile.get('education', 'Not found')}
{breakdown_hint}

Write a professional 2 sentence evaluation explaining why this candidate fits or doesn't fit the role.
Be specific — mention skills or experience depth directly.
DO NOT include HTML tags, bullet points, or labels.
"""

    response = call_llama(prompt)

    # Remove accidental HTML tags and markdown bold
    clean = re.sub(r"<.*?>", "", response)
    clean = re.sub(r"\*+", "", clean)
    return clean.strip()
