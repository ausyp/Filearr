import os
import re
from guessit import guessit


MIN_MOVIE_SIZE_BYTES = 300 * 1024 * 1024


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

    guess = guessit(filename)
    year = guess.get("year")
    title = (guess.get("title") or "").strip()

    if not year:
        return False, "No year in filename", guess

    cleaned = re.sub(r"[^a-zA-Z0-9 ]", "", title).strip()
    if len(cleaned) < 6:
        return False, "Suspicious short title", guess

    return True, None, guess

