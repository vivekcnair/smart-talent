# Smart Talent Engine

## Project Title

**Smart Talent Engine** — AI-Powered Resume Screening and Candidate Ranking System

---

## The Problem

Traditional Applicant Tracking Systems rely on primitive keyword matching, causing recruiters to accidentally reject highly qualified candidates who use different but equivalent terminology. With hundreds of applicants per role, recruiters spend an average of just 6 seconds per resume — leading to missed talent and wasted effort reviewing unqualified candidates who have learned to "keyword stuff" their resumes to game the system.

---

## The Solution

Smart Talent Engine automates resume screening using a three-component AI scoring system that goes far beyond keyword matching. Recruiters paste or upload a Job Description, bulk-upload resumes in any format, and receive a ranked shortlist with a compatibility score breakdown and an AI-written "Summary of Fit" for each top candidate.

**Key Features:**

- **Multi-format ingestion** — accepts PDF, DOCX, JPG, and PNG resumes with adaptive layout parsing for two-column designs, sidebars, and tables
- **Three-component compatibility score** — combines semantic alignment (meaning-based similarity), skill match (regex + LLM-based skill detection), and experience depth (context-aware year extraction) into a single 0–100% score
- **Keyword stuffing detection** — flags candidates who repeat skills without genuine work context, directly countering resume gaming
- **AI-generated Summary of Fit** — LLaMA generates a 2-sentence evaluation for the top 5 candidates explaining exactly why they ranked highly, citing specific skills and experience
- **JD file upload** — job descriptions can be uploaded as PDF or DOCX files in addition to being typed
- **Per-file progress tracking** — each resume shows individual processing progress with specific error messages for corrupt, empty, or unsupported files
- **Batch organisation** — results are tagged with a Job Role label and Batch Date for organised CSV exports across multiple screening sessions

---

## Tech Stack

**Programming Language:**
- Python 3.10+

**Frameworks & UI:**
- Streamlit — web dashboard and user interface

**AI & Machine Learning:**
- Ollama (local) — runs LLaMA 3 locally for profile extraction, skill detection, and summary generation
- LLaMA 3 (`llama3`) via Ollama — large language model for AI tasks
- Sentence Transformers (`all-MiniLM-L6-v2`) — semantic text embedding model for meaning-based similarity
- Scikit-learn — cosine similarity calculation

**Document Parsing:**
- PyMuPDF (`fitz`) — PDF text extraction with adaptive multi-column layout detection
- python-docx — DOCX parsing including tables
- pytesseract + Pillow — OCR for image resumes with contrast enhancement and upscaling

**Data Handling:**
- Pandas — candidate data management, filtering, and CSV export

**Other:**
- Regex (`re`) — context-aware experience extraction and skill pattern matching

---

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.com/download) installed on your machine
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed (for image resumes)

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

**requirements.txt:**
```
streamlit
pymupdf
python-docx
pytesseract
Pillow
sentence-transformers
scikit-learn
pandas
requests
```

---

### Step 4 — Install and Start Ollama

Download Ollama from [https://ollama.com/download](https://ollama.com/download) and install it.

Then pull the LLaMA 3 model:

```bash
ollama pull llama3
```

> **Note:** If your machine has less than 3.5 GB of free RAM, use the smaller model instead:
> ```bash
> ollama pull llama3.2:3b
> ```
> Then open `ai_engine.py` and change `"model": "llama3"` to `"model": "llama3.2:3b"`.

---

### Step 5 — Install Tesseract OCR

Tesseract is required only if you plan to upload image resumes (JPG/PNG).

- **Windows:** Download installer from [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
- **macOS:** `brew install tesseract`
- **Linux:** `sudo apt install tesseract-ocr`

---

### Step 6 — Run the Application

Make sure Ollama is running in the background, then start the app:

```bash
streamlit run app.py
```

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
├── ai_engine.py      ← LLaMA API calls (profile extraction, skill detection, summary)
├── requirements.txt  ← Python dependencies
├── resumes/          ← Uploaded resume files (auto-created)
├── jd_uploads/       ← Uploaded JD files (auto-created)
└── README.md
```

---

## How the Scoring Works

Each resume is scored against the JD using three components:

| Component | Weight | Method |
|---|---|---|
| Skill Match | 35% | Regex pattern matching + LLaMA skill extraction, compared against JD skills |
| Experience Depth | 40% | Context-aware date/duration extraction near work keywords, non-linear scoring curve |
| Semantic Alignment | 25% | `all-MiniLM-L6-v2` embeddings + cosine similarity between resume and JD |

**Final Score = 0.25 × Semantic + 0.35 × Skill + 0.40 × Experience**