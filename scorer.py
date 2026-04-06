from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re

from ai_engine import extract_skills_llm

# Load once at module level
_model = SentenceTransformer("all-MiniLM-L6-v2")


# ─────────────────────────────────────────────
# EXPERIENCE EXTRACTION — CONTEXT-AWARE
# ─────────────────────────────────────────────

# Keywords that indicate a line/section is about WORK experience
_WORK_KEYWORDS = re.compile(
    r"\b(experience|internship|intern|worked|working|employment|employer|"
    r"company|organisation|organization|role|position|designation|job|career|"
    r"developer|engineer|analyst|manager|consultant|full.time|part.time|"
    r"freelance|contract)\b"
)

# Keywords that indicate a line is about EDUCATION — these date ranges must be ignored
_EDUCATION_KEYWORDS = re.compile(
    r"\b(b\.?tech|b\.?e|b\.?sc|m\.?tech|m\.?sc|mba|phd|degree|college|"
    r"university|school|cbse|icse|sslc|hsc|ktu|gpa|cgpa|percentage|batch|"
    r"pursuing|graduated|graduation|class of|passing year)\b"
)


def extract_experience_years(text: str) -> float:
    """
    Extracts ACTUAL work experience years from resume text.

    - Only counts durations/date-ranges that appear near work context keywords
    - Ignores education years (graduation year, board exam years, batch years)
    - Handles "1 Month", "6 months", "X years", and date ranges like "2021–2024"
    - Removed the fallback "assume 2 years if 'experience' keyword found" 
      — that was the main source of false positives
    """
    text_lower = text.lower()
    candidates = []

    # ── Split into lines for context-aware scanning ──
    lines = text_lower.split("\n")

    def _near_work_context(idx: int, window: int = 4) -> bool:
        """Check if any line within ±window lines contains a work keyword."""
        start = max(0, idx - window)
        end = min(len(lines), idx + window + 1)
        for i in range(start, end):
            if _WORK_KEYWORDS.search(lines[i]):
                return True
        return False

    def _is_education_line(line: str) -> bool:
        return bool(_EDUCATION_KEYWORDS.search(line))

    for idx, line in enumerate(lines):
        # Skip lines that are clearly education entries
        if _is_education_line(line):
            continue

        # ── Pattern 1: "X years" / "X+ years" ──
        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b", line):
            val = float(m.group(1))
            if val <= 0 or val > 50:
                continue
            if _near_work_context(idx):
                candidates.append(val)

        # ── Pattern 2: "X months" → fractional years ──
        for m in re.finditer(r"(\d+)\s*(?:months?|mos?)\b", line):
            val = int(m.group(1)) / 12.0
            if _near_work_context(idx):
                candidates.append(val)

        # ── Pattern 3: word-form ("six months", "two years") ──
        word_map = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12
        }
        for word, val in word_map.items():
            if re.search(rf"\b{word}\s+months?\b", line) and _near_work_context(idx):
                candidates.append(val / 12.0)
            if re.search(rf"\b{word}\s+years?\b", line) and _near_work_context(idx):
                candidates.append(float(val))

        # ── Pattern 4: date ranges "2021–2024", "2019–present" ──
        # Only on lines near work context, not education
        if not _near_work_context(idx):
            continue

        for m in re.finditer(
            r"\b(20\d{2}|19\d{2})\s*[-–—/]\s*(20\d{2}|19\d{2}|present|now|current)\b",
            line
        ):
            try:
                start = int(m.group(1))
                end_str = m.group(2)
                end = 2025 if end_str in ("present", "now", "current") else int(end_str)
                duration = end - start
                # Sanity check: work durations should be 0–20 years
                if 1990 <= start <= 2025 and 0 < duration <= 20:
                    candidates.append(float(duration))
            except ValueError:
                pass

    if candidates:
        return round(max(candidates), 1)

    # No fallback assumption — return 0 if nothing found
    return 0.0


# ─────────────────────────────────────────────
# EXPERIENCE → SCORE (NON-LINEAR)
# ─────────────────────────────────────────────
def experience_score(exp_years: float) -> float:
    """
    Non-linear scoring that rewards depth:
    0 yrs → 0 | 0.08 yrs (1 month) → 10 | 1 yr → 45 | 2 yrs → 55 | 5 yrs → 80 | 10 yrs → 100
    """
    if exp_years <= 0:
        return 0.0
    elif exp_years < 1:
        # Sub-year (internships, short stints) — proportional but low
        return exp_years * 40.0
    elif exp_years <= 2:
        return 40.0 + (exp_years / 2.0) * 20.0        # 40–60
    elif exp_years <= 5:
        return 60.0 + ((exp_years - 2.0) / 3.0) * 25.0  # 60–85
    elif exp_years <= 10:
        return 85.0 + ((exp_years - 5.0) / 5.0) * 15.0  # 85–100
    else:
        return 100.0


# ─────────────────────────────────────────────
# SKILL EXTRACTION — KEYWORD FALLBACK
# ─────────────────────────────────────────────
# Skills use word-boundary regex matching to avoid false positives
# e.g. "go" must not match "going", "scala" must not match "scalable"
# Each entry: (canonical_name, regex_pattern)
_SKILL_PATTERNS = [
    # Languages — require word boundaries
    ("python",          r"\bpython\b"),
    ("java",            r"\bjava\b(?!\s*script)"),  # java but not javascript
    ("javascript",      r"\bjavascript\b"),
    ("typescript",      r"\btypescript\b"),
    ("c++",             r"\bc\+\+\b"),
    ("c#",              r"\bc#\b"),
    ("kotlin",          r"\bkotlin\b"),
    ("scala",           r"\bscala\b(?!ble)"),        # scala but not scalable
    ("golang",          r"\bgolang\b"),               # 'go' alone is too ambiguous
    ("ruby",            r"\bruby\b"),
    ("php",             r"\bphp\b"),
    ("swift",           r"\bswift\b"),
    ("rust",            r"\brust\b"),
    ("r",               r"\blanguage r\b|\bprogramming r\b|\busing r\b"),
    # Frontend
    ("react",           r"\breact\b"),
    ("angular",         r"\bangular\b"),
    ("vue",             r"\bvue\.?js\b|\bvuejs\b"),
    ("html",            r"\bhtml\b"),
    ("css",             r"\bcss\b"),
    ("tailwind",        r"\btailwind\b"),
    # Backend frameworks
    ("spring boot",     r"\bspring\s*boot\b"),
    ("spring mvc",      r"\bspring\s*mvc\b"),
    ("spring",          r"\bspring\b"),
    ("django",          r"\bdjango\b"),
    ("flask",           r"\bflask\b"),
    ("fastapi",         r"\bfastapi\b"),
    ("nodejs",          r"\bnode\.?js\b|\bnodejs\b"),
    ("express",         r"\bexpress\.?js\b|\bexpressjs\b"),
    ("dropwizard",      r"\bdropwizard\b"),
    # Databases
    ("mysql",           r"\bmysql\b"),
    ("postgresql",      r"\bpostgresql\b|\bpostgres\b"),
    ("sqlite",          r"\bsqlite\b"),
    ("oracle",          r"\boracle\b"),
    ("mongodb",         r"\bmongo\s*db\b|\bmongodb\b"),  # handles "mongo db" with space
    ("redis",           r"\bredis\b"),
    ("elasticsearch",   r"\belasticsearch\b"),
    ("snowflake",       r"\bsnowflake\b"),
    ("cassandra",       r"\bcassandra\b"),
    ("pl/sql",          r"\bpl[/\-\s]?sql\b|\bplsql\b"),  # pl/sql, pl-sql, pl sql
    ("t-sql",           r"\bt-sql\b|\btsql\b"),
    ("sql",             r"\bsql\b"),
    # Cloud & DevOps
    ("aws",             r"\baws\b|\bamazon web services\b"),
    ("azure",           r"\bazure\b"),
    ("gcp",             r"\bgcp\b|\bgoogle cloud\b"),
    ("docker",          r"\bdocker\b"),
    ("kubernetes",      r"\bkubernetes\b|\bk8s\b"),
    ("terraform",       r"\bterraform\b"),
    ("ansible",         r"\bansible\b"),
    ("jenkins",         r"\bjenkins\b"),
    ("ci/cd",           r"\bci/cd\b|\bcicd\b|\bcontinuous integration\b"),
    ("github actions",  r"\bgithub\s*actions\b"),
    # APIs & Architecture
    ("rest apis",       r"\brest\s*api[s]?\b|\brestful\b"),
    ("graphql",         r"\bgraphql\b"),
    ("microservices",   r"\bmicroservices?\b"),
    ("websocket",       r"\bwebsockets?\b"),
    ("kafka",           r"\bkafka\b|\bapache kafka\b"),
    ("rabbitmq",        r"\brabbitmq\b"),
    ("messaging",       r"\bmessaging\b"),
    # Tools
    ("git",             r"\bgit\b"),
    ("jira",            r"\bjira\b"),
    ("agile",           r"\bagile\b"),
    ("scrum",           r"\bscrum\b"),
    ("linux",           r"\blinux\b"),
    ("power bi",        r"\bpower\s*bi\b"),
    ("tableau",         r"\btableau\b"),
    # ML / Data
    ("machine learning",r"\bmachine\s*learning\b"),
    ("deep learning",   r"\bdeep\s*learning\b"),
    ("nlp",             r"\bnlp\b|\bnatural language processing\b"),
    ("pandas",          r"\bpandas\b"),
    ("numpy",           r"\bnumpy\b"),
    ("scikit-learn",    r"\bscikit[-\s]?learn\b|\bsklearn\b"),
    ("tensorflow",      r"\btensorflow\b"),
    ("pytorch",         r"\bpytorch\b"),
    ("data analysis",   r"\bdata\s*anal[y]?sis\b"),
    ("data engineering",r"\bdata\s*engineering\b"),
    ("etl",             r"\betl\b"),
    # Other
    ("hibernate",       r"\bhibernate\b"),
    ("maven",           r"\bmaven\b"),
    ("gradle",          r"\bgradle\b"),
    ("junit",           r"\bjunit\b"),
    ("selenium",        r"\bselenium\b"),
]

# Pre-compile all patterns
_COMPILED_PATTERNS = [(name, re.compile(pattern)) for name, pattern in _SKILL_PATTERNS]


def _extract_keyword_skills(text: str) -> list:
    """Use regex with word boundaries — avoids false matches like 'go' in 'going'."""
    text_lower = text.lower()
    found = set()
    for name, pattern in _COMPILED_PATTERNS:
        if pattern.search(text_lower):
            found.add(name)
    return list(found)


def _extract_combined_skills(text: str) -> list:
    keyword_skills = _extract_keyword_skills(text)

    try:
        llm_skills = extract_skills_llm(text)
    except Exception:
        llm_skills = []

    # Normalise LLM skills through compiled patterns too
    llm_normalised = set()
    for s in llm_skills:
        if not isinstance(s, str):
            continue
        s_lower = s.lower().strip()
        matched = False
        for name, pattern in _COMPILED_PATTERNS:
            if pattern.search(s_lower):
                llm_normalised.add(name)
                matched = True
                break
        if not matched:
            llm_normalised.add(s_lower)

    combined = set(keyword_skills) | llm_normalised
    return list(combined)


# ─────────────────────────────────────────────
# SKILL MATCH SCORE
# ─────────────────────────────────────────────
def skill_match_score(resume_text: str, jd_text: str) -> float:
    resume_skills = _extract_combined_skills(resume_text)
    jd_skills = _extract_combined_skills(jd_text)

    if not jd_skills:
        return 0.0

    matched = set(resume_skills) & set(jd_skills)
    base = (len(matched) / len(jd_skills)) * 100

    return min(base * 1.15, 100.0)


# ─────────────────────────────────────────────
# KEYWORD STUFFING DETECTOR
# ─────────────────────────────────────────────
def detect_keyword_stuffing(resume_text: str) -> dict:
    lines = resume_text.lower().split("\n")
    stuffed_skills = []

    for skill_name, pattern in _COMPILED_PATTERNS:
        matching_line_indices = [
            idx for idx, line in enumerate(lines)
            if pattern.search(line)
        ]
        total_hits = len(matching_line_indices)

        if total_hits < 5:
            continue

        context_hits = 0
        for idx in matching_line_indices:
            window_start = max(0, idx - 3)
            window_end   = min(len(lines), idx + 4)
            window = " ".join(lines[window_start:window_end])
            if _WORK_KEYWORDS.search(window):
                context_hits += 1

        context_ratio = context_hits / total_hits
        if context_ratio < 0.30:
            stuffed_skills.append(skill_name)

    flagged = len(stuffed_skills) >= 2

    return {
        "flagged":        flagged,
        "stuffed_skills": stuffed_skills,
        "message": (
            f"Possibly keyword stuffed: "
            f"{', '.join(stuffed_skills)} mentioned repeatedly "
            f"without sufficient work context."
        ) if flagged else ""
    }


# ─────────────────────────────────────────────
# MAIN SCORER — RETURNS FULL BREAKDOWN
# ─────────────────────────────────────────────
def calculate_score(resume_text: str, jd_text: str) -> dict:
    """
    Returns a breakdown dict:
    {
        "semantic":   float (0-100),
        "skill":      float (0-100),
        "experience": float (0-100),
        "exp_years":  float,
        "final":      float (0-100)
    }
    Returns all zeros on error.
    """
    zero = {"semantic": 0.0, "skill": 0.0, "experience": 0.0, "exp_years": 0.0, "final": 0.0, "keyword_stuffing": {"flagged": False, "stuffed_skills": [], "message": ""}}

    try:
        r_text = resume_text.lower()[:3500]
        j_text = jd_text.lower()[:1200]

        if not r_text.strip() or not j_text.strip():
            return zero

        # 1. Semantic similarity
        # Resume-JD cosine similarity with all-MiniLM-L6-v2 typically sits
        # between 0.45 and 0.80 for relevant candidates.
        # Old floor of 0.30 was too harsh — pushed most scores under 50%.
        # New calibration:
        #   0.45 raw → 0%  |  0.55 → 29%  |  0.65 → 57%  |  0.75 → 86%  |  0.80 → 100%
        jd_emb = _model.encode(j_text)
        res_emb = _model.encode(r_text)
        raw_sim = float(cosine_similarity([jd_emb], [res_emb])[0][0])
        SIM_FLOOR = 0.45   # below this = 0 semantic contribution
        SIM_CAP   = 0.80   # at/above this = 100 semantic contribution
        semantic = max(0.0, (raw_sim - SIM_FLOOR) / (SIM_CAP - SIM_FLOOR)) * 100
        semantic = min(semantic, 100.0)

        # 2. Skill match
        skill = skill_match_score(r_text, j_text)

        # 3. Experience
        exp_years = extract_experience_years(r_text)
        exp = experience_score(exp_years)

        # Fairness guard: dampen experience only if clearly irrelevant
        if semantic < 25:
            exp *= 0.65

        # ── WEIGHTS ──
        # 50% skill match  — primary signal, directly reflects JD requirements
        # 30% experience   — rewards depth and seniority
        # 20% semantic     — context/domain alignment
        final = round(
            0.20 * semantic +
            0.50 * skill +
            0.30 * exp,
            2
        )

        stuffing = detect_keyword_stuffing(r_text)

        return {
            "semantic":         round(semantic, 2),
            "skill":            round(skill, 2),
            "experience":       round(exp, 2),
            "exp_years":        round(exp_years, 1),
            "final":            final,
            "keyword_stuffing": stuffing
        }

    except Exception as e:
        print(f"[Scorer Error] {e}")
        return zero
