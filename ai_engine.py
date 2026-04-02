import requests
import json
import re

API_KEY = "AIzaSyDf_gt_9Xq_LGMKrwFkof0O7fAcIsNPfTI"

URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={API_KEY}"

def call_gemini(prompt):
    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    try:
        response = requests.post(URL, headers=headers, json=data)

        if response.status_code != 200:
            print("API ERROR:", response.text)
            return ""

        result = response.json()

        return result["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print("Request Error:", e)
        return ""

def extract_profile(text):
    content = ""

    prompt = f"""
    Extract:
    - Skills (list)
    - Experience
    - Education

    Return ONLY JSON.

    Resume:
    {text[:3000]}
    """

    try:
        content = call_gemini(prompt)
        print("RAW:", content)

        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError("No JSON found")

        data = json.loads(match.group())

        return {
            "skills": data.get("skills", []),
            "experience": data.get("experience", "Not found"),
            "education": data.get("education", "")
        }

    except Exception as e:
        print("AI Error:", e)
        print("RAW:", content)

        return {
            "skills": [],
            "experience": "Not found",
            "education": ""
        }