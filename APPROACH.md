# Approach Document — Smart Talent Engine

## Problem Understanding

Traditional Applicant Tracking Systems rely on keyword matching, leading to two major issues: rejection of qualified candidates using different terminology, and ranking of unqualified candidates who keyword-stuff resumes. The objective of this system is to move beyond keyword matching and build an AI-driven solution that understands context, evaluates relevance, and ranks candidates fairly at scale.

---

## Evolution of the Solution

### Initial Rule-Based Approach

The system initially used logical reasoning and regex-based extraction to identify:

- Name  
- Email  
- Skills  
- Experience  
- Education  

However, this approach lacked contextual understanding:

- Reference emails were sometimes incorrectly identified as candidate emails  
- Skills written in unconventional formats were missed  
- Resume format variability reduced accuracy  

---

### AI-Based Extraction Attempt (Gemini API)

To improve accuracy, an AI-based approach using Gemini API was introduced. While it improved contextual extraction, it was not scalable due to:

- API quota limitations  
- Dependency on external services  

---

### Final Solution — Local LLM (LLaMA via Ollama)

The system transitioned to a locally hosted LLM:

- TinyLLaMA was tested but found unreliable  
- LLaMA 3 was adopted for better accuracy  

This provided:

- High-quality contextual extraction  
- No API limits  
- Improved reliability  

---

## System Architecture Overview

The system consists of three major stages:

1. Resume Ingestion & Parsing  
2. Feature Extraction (Skills, Experience, Profile)  
3. Multi-Factor Scoring & Ranking  

---

## Multi-Format Resume Ingestion

The system supports:

- PDF (PyMuPDF)  
- DOCX (python-docx)  
- Images (JPG/PNG via OCR)  

A validation layer ensures:

- Unsupported formats are rejected  
- Corrupt files are flagged  
- Empty files are handled gracefully  

---

## Complex Layout Handling

Resumes often use multi-column layouts. Standard extraction mixes content incorrectly.

Solution:

- Extract text blocks with positional coordinates  
- Dynamically detect column boundaries  
- Reconstruct content in logical reading order  

This ensures accurate parsing of:

- Two-column resumes  
- Sidebars  
- Tables  

---

## Skill Extraction Strategy

A hybrid approach is used:

### Regex-Based Extraction
- Fast and reliable for known technologies  

### LLM-Based Extraction
- Captures implicit and uncommon skills  

### Normalization
- Ensures consistency (e.g., PostgreSQL vs Postgres)  

---

## Experience Extraction

Experience is extracted using:

- Context-aware keyword detection  
- Date range parsing  
- Filtering out education-related timelines  

This ensures accurate calculation of real work experience.

---

## Scoring System

Final Score is calculated as:

Final Score =  
(0.25 × Semantic Alignment) + (0.35 × Skill Match) + (0.40 × Experience)

---

### Why Multi-Factor Scoring?

- Semantic → captures meaning  
- Skills → ensures requirement match  
- Experience → reflects depth  

No single metric is sufficient alone.

---

## Relevance-Based Experience Adjustment

A key issue identified:

- Candidates with irrelevant long experience scoring higher than relevant candidates  

Solution:

- Apply penalty when skill match is low  
- Reduce experience score proportionally  

This ensures fairness and relevance.

---

## AI-Powered Candidate Evaluation

For the top candidates:

- LLaMA generates a 2-sentence summary  
- Explains why the candidate ranked highly  

This provides an **AI-justified shortlist**, improving recruiter trust.

---

## Parallel Processing for Performance

### Implementation

- ThreadPoolExecutor used for parallel processing  
- Each resume processed independently  

### Design Constraint

- LLM calls remain sequential to avoid overload  

### Benefits

- Faster processing for large batches  
- Efficient CPU utilization  
- Real-time progress updates  

---

## User Experience Features

- Bulk upload support  
- Real-time progress tracking  
- Per-file error reporting  
- Clean ranking dashboard  
- CSV export support  

---

## Batch Organization

Each screening session is tagged with:

- Job Role  
- Batch Date  

This enables structured organization and easy retrieval.

---

## Mapping to Problem Requirements

- Multi-format ingestion → PDF, DOCX, JPG, PNG supported  
- Complex layout handling → Coordinate-based parsing implemented  
- Upload progress & error handling → Real-time progress + per-file status  
- Candidate ranking → Multi-factor scoring system  
- Experience prioritization → Highest weight (40%)  
- AI justification → LLaMA-generated summaries  
- Batch organization → Job role and date tagging  

---

## Limitations

- LLM output may occasionally require fallback parsing  
- Experience extraction depends on explicit mentions  
- Semantic similarity may vary for niche domains  
- Requires sufficient RAM for LLaMA  

---

## Summary

The system evolved from a rule-based parser to an AI-driven hybrid engine. By combining:

- Logical extraction  
- LLM-based reasoning  
- Multi-factor scoring  
- Parallel processing  

the solution achieves high accuracy, scalability, and fairness in resume screening.