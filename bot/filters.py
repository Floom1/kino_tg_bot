import re
from typing import Iterable

EXCLUDE_PATTERNS = [
    re.compile(r"\bМУЛЬТ\s+в\s+кино\b", re.IGNORECASE),
    re.compile(r"\bвыпуск\s*№?\s*\d+\b", re.IGNORECASE),
]

# Matches variations like " - предсеансовое обслуживание \"...\"" with hyphen types and quotes optional
PRESESSION_SUFFIX_RE = re.compile(
    r"\s*[\-–—]\s*предсеансовое\s+обслуживание(?:\s+['\"«»“”‘’].*?['\"«»“”‘’])?\s*$",
    re.IGNORECASE,
)

SURROUNDING_QUOTES_RE = re.compile(r'^[\'\"«»“”‘’]+|[\'\"«»“”‘’]+$')

GENERIC_TITLES = {
    # sections / generic labels
    "расписание фильмов", "рекомендации для вас", "рестораны рядом", "популярно сейчас",
    "смотреть в okko", "как вам кинотеатр?", "отзывы", "подборки афиши", "все",
    # genres
    "боевики", "военные", "детективы", "драматические", "исторические", "комедии", "мелодрамы", "приключения", "слешеры", "триллеры", "ужасы", "фэнтези",
}

# Normalized labels without spaces/punct to catch glued words like "ОтзывыВсе"
GENERIC_LABEL_KEYS = {
    "отзывывсе",
    "подборкиафиши",
    "подборкиафишивсе",
}

PUNCT_WS_RE = re.compile(r"[\s\.,:;!\?\-–—_/\\]+")


def normalize_title(title: str) -> str:
    t = title.strip()
    t = re.sub(r"\s+", " ", t)
    return t


def strip_surrounding_quotes(title: str) -> str:
    return SURROUNDING_QUOTES_RE.sub("", title).strip()


def clean_title(title: str) -> str:
    # Remove known suffix like "- предсеансовое обслуживание 'X'"
    cleaned = PRESESSION_SUFFIX_RE.sub("", title)
    cleaned = strip_surrounding_quotes(cleaned)
    return cleaned.strip()


def to_label_key(s: str) -> str:
    # Lowercase, remove spaces and punctuation for robust generic matching
    return PUNCT_WS_RE.sub("", s.lower())


def is_generic_label(title_lower: str) -> bool:
    if title_lower in GENERIC_TITLES:
        return True
    if to_label_key(title_lower) in GENERIC_LABEL_KEYS:
        return True
    return False


def is_valid_movie_title(title: str) -> bool:
    if not title:
        return False
    for pat in EXCLUDE_PATTERNS:
        if pat.search(title):
            return False
    title_lower = title.lower()
    if is_generic_label(title_lower):
        return False
    # Heuristics: exclude very short or obviously non-title lines
    if len(title) < 2:
        return False
    return True


def filter_movie_titles(titles: Iterable[str]) -> list[str]:
    result: list[str] = []
    for raw in titles:
        t = normalize_title(raw)
        t = clean_title(t)
        if is_valid_movie_title(t):
            result.append(t)
    # deduplicate preserving order
    seen = set()
    uniq: list[str] = []
    for t in result:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq
