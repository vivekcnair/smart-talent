# Smart Talent Engine

## Project Title

Smart Talent Engine – Resume Screening and Candidate Ranking System

---

## The Problem

Recruiters often have to go through a large number of resumes manually, which takes a lot of time. Most existing systems only use keyword matching, so they may miss good candidates who don’t use exact keywords.

---

## The Solution

This project helps automate the resume screening process. It reads resumes in different formats, extracts useful information, and compares them with a job description to find the best candidates.

Instead of simple keyword matching, it uses semantic similarity to understand how well a resume matches the job role.

Main features:

* Supports PDF, DOCX, and image resumes
* Extracts text using OCR when needed
* Calculates similarity score between resume and job description
* Ranks candidates based on score
* Allows filtering by skills
* Shows results in a simple dashboard
* Option to download results as CSV

---

## Tech Stack

Programming Language:

* Python

Libraries and Tools:

* Streamlit (for dashboard)
* Sentence Transformers (for similarity scoring)
* Scikit-learn (cosine similarity)
* PyMuPDF (PDF reading)
* python-docx (Word files)
* pytesseract and Pillow (image text extraction)
* Pandas (data handling)

AI / API:

* Google Gemini API (used for extracting details and generating summary)

---

## Setup Instructions

1. Clone the repository

git clone https://github.com/your-username/smart-talent-engine.git
cd smart-talent-engine

---

2. Create virtual environment

python -m venv venv
venv\Scripts\activate

---

3. Install dependencies

pip install -r requirements.txt

---

4. Add API key

Open `ai_engine.py` and replace:

API_KEY = "YOUR_GEMINI_API_KEY"

with your own key.

---

5. Run the app

streamlit run app.py

---

6. Open in browser

http://localhost:8501

---

## Project Structure

smart-talent-engine/
│
├── app.py
├── parser.py
├── scorer.py
├── ai_engine.py
├── requirements.txt
├── resumes/
└── README.md

---

## Future Improvements

* Improve accuracy of skill and experience detection
* Add better scoring based on experience
* Deploy the project online
* Add login system for users

---


