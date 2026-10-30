import os
import re
from guessit import guessit


MIN_MOVIE_SIZE_BYTES = 300 * 1024 * 1024
LANGUAGE_WORDS = re.compile(r"(?i)\b(malayalam|tamil|telugu|hindi|kannada|english|multi audio|dual audio)\b")


def clean_filename(filename: str) -> str:
    """
    Tidy a release name before guessit sees it: non-breaking spaces become spaces
    ("Prathichaya_2026\xa0Malayalam" hides the year), leading "_" / "." are dropped, and so is a
    numbered-list prefix ("1970 - Apocalypse.Z.New.World.2026" would otherwise be titled "1970").
    """
    text = re.sub(r"[\u00a0\u2000-\u200b\u202f\u3000]", " ", filename)
    text = text.lstrip("_. ")
    # Only when a worded title follows, so "1917 - 2019 1080p" and "1986 - Malayalam 2024" keep theirs
    match = re.match(r"\d{1,4}\s*-\s+(?=[^\W\d_])", text)
    if match and not LANGUAGE_WORDS.match(text, match.end()):
        text = text[match.end():]
    return text


def extract_filename_language(filename: str):
    """Returns a normalized 3-letter language code if present in filename, else None."""
    name = filename.lower()
    checks = {
        "mal": ["malayalam", " mal ", ".mal.", "_mal_", "-mal-"],
        "tam": ["tamil", " tam ", ".tam.", "_tam_", "-tam-"],
        "hin": ["hindi", " hin ", ".hin.", "_hin_", "-hin-"],
        "tel": ["telugu", " tel ", ".tel.", "_tel_", "-tel-"],
        "eng": ["english", " eng ", ".eng.", "_eng_", "-eng-"],
    }
    for code, patterns in checks.items():
        if any(p in name for p in patterns):
            return code
    return None


def evaluate_safety(path: str):
    """
    Evaluate mandatory safety checks before metadata lookups.
    Returns (allowed, reason, guess_data).
    """
    filename = os.path.basename(path)
    lower_filename = filename.lower()

    # Absolute pre-parse guards
    if "sample" in lower_filename:
        return False, "Sample file", None

    try:
        size = os.path.getsize(path)
        if size < MIN_MOVIE_SIZE_BYTES:
            return False, "Too small to be full movie", None
    except OSError:
        return False, "Unable to determine file size", None

    guess = guessit(clean_filename(filename))
    year = guess.get("year")
    title = (guess.get("title") or "").strip()

    if not year:
        return False, "No year in filename", guess

    # Short real titles ("Gu", "Cup", "Haal") are allowed; the TMDB lookup
    # requires an exact title match for them instead of rejecting them here
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", title)
    if len(cleaned) < 2:
        return False, "Suspicious short title", guess

    return True, None, guess

