from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re

from ai_engine import extract_skills_llm

_model = SentenceTransformer("all-MiniLM-L6-v2")

_WORK_KEYWORDS = re.compile(
    r"\b(experience|internship|intern|worked|working|employment|employer|"
    r"company|organisation|organization|role|position|designation|job|career|"
    r"developer|engineer|analyst|manager|consultant|full.time|part.time|"
    r"freelance|contract)\b"
)

_EDUCATION_KEYWORDS = re.compile(
    r"\b(b\.?tech|b\.?e|b\.?sc|m\.?tech|m\.?sc|mba|phd|degree|college|"
    r"university|school|cbse|icse|sslc|hsc|ktu|gpa|cgpa|percentage|batch|"
    r"pursuing|graduated|graduation|class of|passing year)\b"
)


def extract_experience_years(text: str) -> float:
    text_lower = text.lower()
    candidates = []

    lines = text_lower.split("\n")

    def _near_work_context(idx: int, window: int = 4) -> bool:
        start = max(0, idx - window)
        end = min(len(lines), idx + window + 1)
        for i in range(start, end):
            if _WORK_KEYWORDS.search(lines[i]):
                return True
        return False

    def _is_education_line(line: str) -> bool:
        return bool(_EDUCATION_KEYWORDS.search(line))

    for idx, line in enumerate(lines):
        if _is_education_line(line):
            continue

        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b", line):
            val = float(m.group(1))
            if val <= 0 or val > 50:
                continue
            if _near_work_context(idx):
                candidates.append(val)

        for m in re.finditer(r"(\d+)\s*(?:months?|mos?)\b", line):
            val = int(m.group(1)) / 12.0
            if _near_work_context(idx):
                candidates.append(val)

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

        if not _near_work_context(idx):
            continue

        for m in re.finditer(
            r"\b(20\d{2}|19\d{2})\s*[-–—/]\s*(20\d{2}|19\d{2}|present|now|current)\b",
            line
        ):
            try:
                start = int(m.group(1))
                end_str = m.group(2)
                end = 2026 if end_str in ("present", "now", "current") else int(end_str)
                duration = end - start
                if 1990 <= start <= 2026 and 0 < duration <= 20:
                    candidates.append(float(duration))
            except ValueError:
                pass

    if candidates:
        return round(max(candidates), 1)

    return 0.0


def experience_score(exp_years: float) -> float:
    if exp_years <= 0:
        return 0.0
    elif exp_years < 1:
        return exp_years * 40.0
    elif exp_years <= 2:
        return 40.0 + (exp_years / 2.0) * 20.0
    elif exp_years <= 5:
        return 60.0 + ((exp_years - 2.0) / 3.0) * 25.0
    elif exp_years <= 10:
        return 85.0 + ((exp_years - 5.0) / 5.0) * 15.0
    else:
        return 100.0


_SKILL_PATTERNS = [
    ("python",          r"\bpython\b"),
    ("java",            r"\bjava\b(?!\s*script)"),
    ("javascript",      r"\bjavascript\b"),
    ("typescript",      r"\btypescript\b"),
    ("c++",             r"\bc\+\+\b"),
    ("c#",              r"\bc#\b"),
    ("kotlin",          r"\bkotlin\b"),
    ("scala",           r"\bscala\b(?!ble)"),
    ("golang",          r"\bgolang\b"),
    ("ruby",            r"\bruby\b"),
    ("php",             r"\bphp\b"),
    ("swift",           r"\bswift\b"),
    ("rust",            r"\brust\b"),
    ("r",               r"\blanguage r\b|\bprogramming r\b|\busing r\b"),
    ("react",           r"\breact\b"),
    ("angular",         r"\bangular\b"),
    ("vue",             r"\bvue\.?js\b|\bvuejs\b"),
    ("html",            r"\bhtml\b"),
    ("css",             r"\bcss\b"),
    ("tailwind",        r"\btailwind\b"),
    ("spring boot",     r"\bspring\s*boot\b"),
    ("spring mvc",      r"\bspring\s*mvc\b"),
    ("spring",          r"\bspring\b"),
    ("django",          r"\bdjango\b"),
    ("flask",           r"\bflask\b"),
    ("fastapi",         r"\bfastapi\b"),
    ("nodejs",          r"\bnode\.?js\b|\bnodejs\b"),
    ("express",         r"\bexpress\.?js\b|\bexpressjs\b"),
    ("dropwizard",      r"\bdropwizard\b"),
    ("mysql",           r"\bmysql\b"),
    ("postgresql",      r"\bpostgresql\b|\bpostgres\b"),
    ("sqlite",          r"\bsqlite\b"),
    ("oracle",          r"\boracle\b"),
    ("mongodb",         r"\bmongo\s*db\b|\bmongodb\b"),
    ("redis",           r"\bredis\b"),
    ("elasticsearch",   r"\belasticsearch\b"),
    ("snowflake",       r"\bsnowflake\b"),
    ("cassandra",       r"\bcassandra\b"),
    ("pl/sql",          r"\bpl[/\-\s]?sql\b|\bplsql\b"),
    ("t-sql",           r"\bt-sql\b|\btsql\b"),
    ("sql",             r"\bsql\b"),
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
    ("rest apis",       r"\brest\s*api[s]?\b|\brestful\b"),
    ("graphql",         r"\bgraphql\b"),
    ("microservices",   r"\bmicroservices?\b"),
    ("websocket",       r"\bwebsockets?\b"),
    ("kafka",           r"\bkafka\b|\bapache kafka\b"),
    ("rabbitmq",        r"\brabbitmq\b"),
    ("messaging",       r"\bmessaging\b"),
    ("git",             r"\bgit\b"),
    ("jira",            r"\bjira\b"),
    ("agile",           r"\bagile\b"),
    ("scrum",           r"\bscrum\b"),
    ("linux",           r"\blinux\b"),
    ("power bi",        r"\bpower\s*bi\b"),
    ("tableau",         r"\btableau\b"),
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
    ("hibernate",       r"\bhibernate\b"),
    ("maven",           r"\bmaven\b"),
    ("gradle",          r"\bgradle\b"),
    ("junit",           r"\bjunit\b"),
    ("selenium",        r"\bselenium\b"),
]

_COMPILED_PATTERNS = [(name, re.compile(pattern)) for name, pattern in _SKILL_PATTERNS]


def _extract_keyword_skills(text: str) -> list:
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


def skill_match_score(resume_text: str, jd_text: str) -> float:
    resume_skills = _extract_combined_skills(resume_text)
    jd_skills = _extract_combined_skills(jd_text)

    if not jd_skills:
        return 0.0

    matched = set(resume_skills) & set(jd_skills)
    base = (len(matched) / len(jd_skills)) * 100

    return min(base * 1.15, 100.0)


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


def calculate_score(resume_text: str, jd_text: str) -> dict:
    zero = {
        "semantic": 0.0, "skill": 0.0, "experience": 0.0,
        "exp_years": 0.0, "final": 0.0,
        "keyword_stuffing": {"flagged": False, "stuffed_skills": [], "message": ""}
    }

    try:
        r_text = resume_text.lower()[:3500]
        j_text = jd_text.lower()[:1200]

        if not r_text.strip() or not j_text.strip():
            return zero

        jd_emb = _model.encode(j_text)
        res_emb = _model.encode(r_text)
        raw_sim = float(cosine_similarity([jd_emb], [res_emb])[0][0])
        SIM_FLOOR = 0.45
        SIM_CAP   = 0.80
        semantic = max(0.0, (raw_sim - SIM_FLOOR) / (SIM_CAP - SIM_FLOOR)) * 100
        semantic = min(semantic, 100.0)

        skill = skill_match_score(r_text, j_text)

        exp_years = extract_experience_years(r_text)
        exp = experience_score(exp_years)

        if semantic < 25:
            exp *= 0.65

        # Weights: Semantic 25% | Skill 35% | Experience 40%
        # (matches the scoring table documented in README.md)
        final = round(
            0.25 * semantic +
            0.35 * skill +
            0.40 * exp,
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
