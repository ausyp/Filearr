import os
import re
import logging

import tmdbsimple as tmdb
from guessit import guessit

from backend.core.config_service import config_service
from backend.core.decision import Decision, sanitize_filename, extract_quality_tags
from backend.core.tmdb import normalize_title, is_similar, MIN_SIMILARITY, SHORT_TITLE_LENGTH

logger = logging.getLogger(__name__)

MIN_EPISODE_SIZE_BYTES = 30 * 1024 * 1024  # daily serial episodes at 480p can be ~100 MB
INDIAN_BONUS = 0.1  # prefer Indian shows when titles score alike ("Bigg Boss" IN vs others)

# "Epi 45", "Ep.12", "Episode 1045" -> "E45": guessit misses some of these
EPISODE_WORD = re.compile(r"(?i)(?<![a-z0-9])(?:epi|ep|episode)[\s._-]*(\d{1,4})(?![0-9])")
# Language words often tacked onto Indian show names ("Bigg Boss Malayalam", "Kerala Crime Files Malayalam")
LANGUAGE_WORDS = re.compile(r"(?i)\b(malayalam|tamil|telugu|hindi|kannada|bengali|marathi)\b")


def parse_episode(filename):
    """
    Returns guessit data when the filename looks like a TV episode
    (SxxExx, "Ep 123", "Episode 45" or an air date), else None.
    """
    guess = guessit(EPISODE_WORD.sub(r" E\1 ", filename))
    if guess.get("type") != "episode" or not guess.get("title"):
        return None
    if guess.get("episode") is None and not guess.get("date"):
        return None  # a season pack or something guessit is unsure about
    return guess


def show_title_score(title, result):
    candidates = [result.get("name"), result.get("original_name")]
    candidates += [c.split(":")[0] for c in candidates if c and ":" in c]
    return max((is_similar(title, c) for c in candidates if c), default=0.0)


def is_indian(result):
    return "IN" in (result.get("origin_country") or [])


def pick_best_show(title, results, strict):
    """Best scoring show above the threshold, with Indian shows preferred, or None."""
    best, best_score = None, 0.0
    for res in results:
        score = show_title_score(title, res)
        if strict and score < 1.0:
            continue
        if score < MIN_SIMILARITY:
            continue
        if is_indian(res):
            score += INDIAN_BONUS
        if score > best_score:
            best, best_score = res, score
    return best


def search_titles(title):
    """The title as parsed, then without a trailing language word."""
    titles = [title]
    stripped = re.sub(r"\s+", " ", LANGUAGE_WORDS.sub(" ", title)).strip()
    if stripped and stripped.lower() != title.lower():
        titles.append(stripped)
    return titles


def get_show_metadata(guess):
    tmdb_key = config_service.get_setting("TMDB_API_KEY")
    if tmdb_key:
        tmdb.API_KEY = tmdb_key
    title = guess.get("title")

    try:
        search = tmdb.Search()
        for query in search_titles(title):
            strict = len(normalize_title(query).replace(" ", "")) < SHORT_TITLE_LENGTH
            results = search.tv(query=query).get("results", [])
            best = pick_best_show(query, results, strict)
            if best:
                return {
                    "title": best["name"],
                    "year": (best.get("first_air_date") or "")[:4] or "Unknown",
                    "tmdb_id": best["id"],
                    "original_language": best.get("original_language", "und"),
                    "indian": is_indian(best),
                }
        logger.warning(f"No confident TMDB TV match for '{title}'")
    except Exception as e:
        logger.error(f"TMDB TV lookup failed for '{title}': {e}")
    return None


def episode_label(guess):
    """'S01E05', 'S01E05-E06', or the air date for daily shows with no episode number."""
    episode = guess.get("episode")
    if episode is None:
        return guess["date"].isoformat()
    season = guess.get("season") or 1
    if isinstance(season, list):
        season = season[0]
    episodes = episode if isinstance(episode, list) else [episode]
    label = f"S{season:02d}E{episodes[0]:02d}"
    if len(episodes) > 1:
        label += f"-E{episodes[-1]:02d}"
    return label


def season_folder(guess):
    if guess.get("episode") is None:
        return f"Season {guess['date'].year}"
    season = guess.get("season") or 1
    if isinstance(season, list):
        season = season[0]
    return f"Season {season:02d}"


def decide_episode(file_path, language, guess, show):
    """Destination: TV root/Show (Year)/Season XX/Show - SxxExx [quality].ext"""
    config = config_service.get_all_settings()
    destination_root = config.get("TV_DIR", "/media/tv-shows")
    if language == "mal":
        destination_root = config.get("MALAYALAM_TV_DIR", "/media/tv-shows/malayalam-tv-shows")

    title = sanitize_filename(show.get("title", "Unknown"))
    year = str(show.get("year") or "Unknown")
    show_folder = f"{title} ({year})" if year != "Unknown" else title

    ext = os.path.splitext(file_path)[1].lower()
    quality_tags = extract_quality_tags(file_path)
    file_stem = f"{title} - {episode_label(guess)} {quality_tags}".strip()

    return Decision(
        action="move",
        destination=os.path.join(destination_root, show_folder, season_folder(guess), f"{file_stem}{ext}"),
        reason=f"Processed TV episode (Language: {language})",
    )
