# Smart Talent Engine

## Project Title

**Smart Talent Engine** — AI-Powered Resume Screening and Candidate Ranking System

---

## The Problem

Traditional Applicant Tracking Systems rely on primitive keyword matching, causing recruiters to accidentally reject highly qualified candidates who use different but equivalent terminology. With hundreds of applicants per role, recruiters spend an average of just 6 seconds per resume — leading to missed talent and wasted effort reviewing unqualified candidates who have learned to keyword stuff their resumes to game the system.

---

## The Solution

Smart Talent Engine automates resume screening using a three-component AI scoring system that goes far beyond keyword matching. Recruiters paste or upload a Job Description, bulk-upload resumes in any format, and receive a ranked shortlist with a compatibility score breakdown and an AI-written Summary of Fit for each top candidate.

**Key Features:**

- **Multi-format ingestion** — accepts PDF, DOCX, JPG, and PNG resumes with adaptive layout parsing for two-column designs, sidebars, and tables
- **Three-component compatibility score** — combines semantic alignment, skill match, and experience depth into a single 0–100% score
- **Candidate name extraction** — LLaMA extracts the candidate's full name from each resume so results show the actual name instead of a filename
- **Keyword stuffing detection** — flags candidates who repeat skills without genuine work context, directly countering resume gaming
- **AI-generated Summary of Fit** — LLaMA generates a 2-sentence evaluation for the top 5 candidates explaining why they ranked highly
- **JD file upload** — job descriptions can be uploaded as PDF or DOCX in addition to being typed
- **Ollama auto-management** — Ollama starts automatically when the app launches and can be stopped from the sidebar
- **Parallel processing** — multiple resumes are processed simultaneously with a configurable worker count
- **Batch organisation** — results are tagged with a Job Role label and Batch Date for organised CSV exports

---

## How the Scoring Works

Each resume is evaluated against the Job Description using three components that are combined into a final compatibility score.

### 1. Semantic Alignment (25%)

The full resume text and JD are each converted into a numerical vector using the `all-MiniLM-L6-v2` sentence embedding model. Cosine similarity is then measured between the two vectors — this captures meaning-level relevance rather than just word overlap. A resume that says "built distributed systems" and a JD that says "microservices architecture" will still score well here even though the exact words differ.

### 2. Skill Match (35%)

Skills are extracted from both the resume and JD using two methods combined — a regex pattern library covering 80+ technologies, and LLaMA-based extraction to catch skills the regex might miss. The matched skills are compared and scored as a percentage of the JD's required skills, with a small bonus for exceeding the requirement. This is the most reliable signal and carries the highest weight.

### 3. Experience Depth (40%)

Experience years are extracted using context-aware parsing — the system looks for year mentions, date ranges, and duration phrases only near work-related keywords like "role", "developer", "employment", etc. to avoid counting education years. If a total experience figure is explicitly stated it is used directly; otherwise date ranges across roles are merged and summed. The raw years are then converted to a score on a non-linear curve that rewards early career growth more steeply:

| Experience | Score |
|---|---|
| 1 year | 50% |
| 2 years | 60% |
| 3 years | 68% |
| 5 years | 85% |
| 10 years | 100% |

Experience carries the highest weight because it is the hardest signal to fake.

### Relevance Penalty

If a candidate's skill match score is below 30%, their experience score is partially penalised — a strong penalty at under 15% skill match and a mild penalty between 15–30%. This ensures that candidates with many years of experience in an unrelated field do not rank above genuinely relevant candidates with fewer years.

### Final Score

```
Final = (0.25 × Semantic) + (0.35 × Skill) + (0.40 × Experience)
```

---

## Tech Stack

**Programming Language:**
- Python 3.10+

**Frameworks & UI:**
- Streamlit

**AI & Machine Learning:**
- Ollama — runs LLaMA 3 locally for profile extraction, skill detection, and summary generation
- LLaMA 3 (`llama3`) via Ollama API
- Sentence Transformers (`all-MiniLM-L6-v2`) — semantic text embeddings
- Scikit-learn — cosine similarity calculation

**Document Parsing:**
- PyMuPDF (`fitz`) — PDF extraction with adaptive multi-column layout detection
- python-docx — DOCX parsing including tables
- pytesseract + Pillow — OCR for image resumes with contrast enhancement

**Data Handling:**
- Pandas — candidate data management, filtering, and CSV export

**Other:**
- Regex (`re`) — context-aware experience extraction and skill pattern matching
- concurrent.futures — parallel resume processing

---

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.com/download) installed on your machine
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed (only needed for JPG/PNG resumes)

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/smart-talent-engine.git
cd smart-talent-engine
```

---

### Step 2 — Create and Activate a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

---

### Step 3 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4 — Pull the LLaMA 3 Model

```bash
ollama pull llama3
```

> If your machine has less than 3.5 GB of free RAM, use the smaller model instead:
> ```bash
> ollama pull llama3.2:3b
> ```
> Then open `ai_engine.py` and change `"model": "llama3"` to `"model": "llama3.2:3b"`.

---

### Step 5 — Install Tesseract OCR (optional)

Only required if you plan to upload image resumes (JPG/PNG).

- **Windows:** Download from [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
- **macOS:** `brew install tesseract`
- **Linux:** `sudo apt install tesseract-ocr`

---

### Step 6 — Run the Application

```bash
streamlit run app.py
```

Ollama starts automatically when the app launches. No need to run it separately in another terminal.

---

### Step 7 — Open in Browser

```
http://localhost:8501
```

---

## Project Structure

```
smart-talent-engine/
│
├── app.py            ← Streamlit dashboard (UI, upload, results display)
├── parser.py         ← Resume text extraction (PDF, DOCX, image)
├── scorer.py         ← Scoring engine (semantic + skill + experience + stuffing detection)
├── ai_engine.py      ← LLaMA API calls + Ollama process management
├── requirements.txt  ← Python dependencies
├── resumes/          ← Uploaded resume files (auto-created)
├── jd_uploads/       ← Uploaded JD files (auto-created)
└── README.md
```

---
