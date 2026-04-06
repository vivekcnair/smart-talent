import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""

    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&[a-z]+;", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

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

def extract_json(text: str) -> dict:
    try:
        text = re.sub(r"```(?:json)?", "", text).strip()

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            json_str = match.group()
            json_str = re.sub(r",\s*}", "}", json_str)
            json_str = re.sub(r",\s*]", "]", json_str)
            return json.loads(json_str)

    except Exception as e:
        print(f"JSON Parse Error: {e}")

    return {}

def extract_profile(text: str) -> dict:
    prompt = f"""
You are an AI resume parser.

Extract:
- name (full name of the candidate)
- skills (list)
- experience (short summary)
- education

Return ONLY JSON:
{{
  "name": "",
  "skills": [],
  "experience": "",
  "education": ""
}}

Resume:
{text[:3000]}
"""

    content = call_llama(prompt)
    data = extract_json(content)

    skills = data.get("skills", [])
    if isinstance(skills, str):
        skills = [s.strip() for s in re.split(r"[,;]", skills) if s.strip()]

    skills = [clean_text(s) for s in skills if isinstance(s, str)]

    education = data.get("education", "")
    if isinstance(education, list):
        education = " | ".join([clean_text(str(e)) for e in education])
    elif isinstance(education, dict):
        education = clean_text(str(education))

    name = data.get("name", "")
    if isinstance(name, str):
        name = clean_text(name)

    return {
        "name": name or "Unknown",
        "skills": skills,
        "experience": clean_text(data.get("experience", "Not found")),
        "education": education or "Not found"
    }

def extract_skills_llm(text: str) -> list:
    prompt = f"""
Extract ONLY technical skills as a JSON list. Return ONLY the JSON list, no explanation, no markdown.

Example output: ["Python", "Docker", "PostgreSQL"]

Text:
{text[:2000]}
"""

    response = call_llama(prompt)

    if not response:
        return []

    response = re.sub(r"```(?:json)?", "", response).strip()
    response = response.replace("```", "").strip()

    try:
        result = json.loads(response)
        if isinstance(result, list):
            return [clean_text(s.lower()) for s in result if isinstance(s, str)]
    except Exception:
        pass

    try:
        match = re.search(r"\[.*?\]", response, re.DOTALL)
        if match:
            arr_str = match.group()
            arr_str = re.sub(r",\s*]", "]", arr_str)
            result = json.loads(arr_str)
            if isinstance(result, list):
                return [clean_text(s.lower()) for s in result if isinstance(s, str)]
    except Exception:
        pass

    try:
        found = re.findall(r'"([^"]{2,50})"', response)
        if found:
            return [clean_text(s.lower()) for s in found]
    except Exception:
        pass

    return []

def generate_summary(profile: dict, jd_text: str, score_breakdown: dict = None) -> str:
    skills = ", ".join([clean_text(s) for s in profile.get("skills", [])])
    experience = clean_text(profile.get("experience", ""))
    education = clean_text(profile.get("education", ""))

    breakdown_hint = ""
    if score_breakdown:
        breakdown_hint = f"""
Scores:
Semantic: {round(score_breakdown.get('semantic', 0), 1)}%
Skill: {round(score_breakdown.get('skill', 0), 1)}%
Experience: {round(score_breakdown.get('experience', 0), 1)}%
Overall: {round(score_breakdown.get('final', 0), 1)}%
"""

    prompt = f"""
Job Description:
{jd_text[:800]}

Candidate:
Skills: {skills}
Experience: {experience}
Education: {education}
{breakdown_hint}

STRICT RULES:
- Output MUST be plain text only
- NO HTML, NO markdown, NO symbols like < >
- ONLY 2 sentences

Write a professional evaluation.
"""

    response = call_llama(prompt)

    return clean_text(response)
