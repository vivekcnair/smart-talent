from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re

model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_experience_years(text):
    matches = re.findall(r'(\d+)\+?\s*(years|yrs)', text.lower())

    if matches:
        years = [int(m[0]) for m in matches]
        return max(years)

    return 0

def calculate_score(resume_text, jd_text):
    try:
        resume_text = resume_text.lower()[:3000]
        jd_text = jd_text.lower()[:1000]

        if not resume_text.strip() or not jd_text.strip():
            return 0

        jd_embedding = model.encode(jd_text)
        resume_embedding = model.encode(resume_text)

        similarity = cosine_similarity(
            [jd_embedding],
            [resume_embedding]
        )[0][0]

        similarity_score = similarity * 100

        exp_years = extract_experience_years(resume_text)
        exp_score = min(exp_years / 10, 1) * 100

        final_score = (0.7 * similarity_score) + (0.3 * exp_score)

        return round(final_score, 2)

    except Exception as e:
        print(f"Error in scoring: {e}")
        return 0