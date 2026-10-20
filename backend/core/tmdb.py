import tmdbsimple as tmdb
from guessit import guessit
from backend.core.config_service import config_service
import logging
import difflib
import re
import unicodedata
import os
from functools import lru_cache

from backend.core.safety import clean_filename, extract_filename_language

logger = logging.getLogger(__name__)

MIN_SIMILARITY = 0.7
SHORT_TITLE_LENGTH = 6  # titles shorter than this need an exact TMDB match
TOKEN_MATCH_RATIO = 0.85  # "kaandam" ~ "kandam", "terminator" ~ "terminators"
YEAR_BONUS = 0.1  # TMDB year equals the filename year
LANGUAGE_BONUS = 0.05  # film is in the language the filename names
REGIONAL_BONUS = 0.02  # Indian film for an Indian-language filename
ALT_TITLE_LOOKUPS = 5  # results per search whose alternative titles are checked
HOME_RELEASE_TYPES = {4, 5, 6}  # TMDB release types: digital, physical, TV

# Filename language (safety.extract_filename_language) -> TMDB original_language
TMDB_LANGUAGES = {"mal": "ml", "tam": "ta", "hin": "hi", "tel": "te", "eng": "en"}
INDIAN_LANGUAGES = {"ml", "ta", "hi", "te", "kn", "bn", "mr", "pa", "gu"}
LANGUAGE_WORDS = re.compile(r"(?i)\b(malayalam|tamil|telugu|hindi|kannada|english|multi audio|dual audio)\b")

def normalize_title(title):
    """Lowercase, strip accents/punctuation, '&' -> 'and', drop a leading article."""
    text = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode()
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"^(the|a|an) ", "", text)

def is_similar(str1, str2):
    """
    Title similarity in [0, 1]. Every word has to line up: extra or missing words
    pull the score down, so "Terminator 2" doesn't match "Angel Terminators 2".
    """
    s1, s2 = normalize_title(str1), normalize_title(str2)
    if not s1 or not s2:
        return 0.0
    if s1 == s2 or s1.replace(" ", "") == s2.replace(" ", ""):  # "Baby Girl" == "Babygirl"
        return 1.0

    tokens1, tokens2 = s1.split(), s2.split()
    if len(tokens1) == 1 and len(tokens2) == 1:
        # Single words must match exactly ("Arya" is not "Aryan")
        return 0.0

    matched = 0
    remaining = list(tokens2)
    for token in tokens1:
        best = max(remaining, key=lambda t: difflib.SequenceMatcher(None, token, t).ratio(), default=None)
        if best is not None and difflib.SequenceMatcher(None, token, best).ratio() >= TOKEN_MATCH_RATIO:
            matched += 1
            remaining.remove(best)
    token_score = matched / max(len(tokens1), len(tokens2))
    seq_ratio = difflib.SequenceMatcher(None, s1, s2).ratio()
    return min(seq_ratio, token_score)

def title_score(title, result, extra_titles=()):
    """Best similarity against the TMDB title, original title, alternative titles, and the title before a subtitle colon."""
    candidates = [result.get("title"), result.get("original_title"), *extra_titles]
    candidates += [c.split(":")[0] for c in candidates if c and ":" in c]  # "Pushpa 2" vs "Pushpa 2: The Rule"
    return max((is_similar(title, c) for c in candidates if c), default=0.0)

@lru_cache(maxsize=512)  # failures raise, so they aren't cached
def _alternative_titles(movie_id):
    return tuple(t.get("title") for t in tmdb.Movies(movie_id).alternative_titles().get("titles", []))

@lru_cache(maxsize=512)
def _release_years(movie_id):
    results = tmdb.Movies(movie_id).release_dates().get("results", [])
    return frozenset(
        d.get("release_date", "")[:4]
        for country in results for d in country.get("release_dates", [])
        if d.get("type") in HOME_RELEASE_TYPES
    ) - {""}

def alternative_titles(movie_id):
    """Other names TMDB knows a film by ("Daayam" for "Inheritance"), or () if the lookup fails."""
    try:
        return _alternative_titles(movie_id)
    except Exception as e:
        logger.warning(f"TMDB alternative titles lookup failed for {movie_id}: {e}")
        return ()

def release_years(movie_id):
    """Years the film came out on streaming, disc or TV anywhere, or an empty set if the lookup fails."""
    try:
        return _release_years(movie_id)
    except Exception as e:
        logger.warning(f"TMDB release dates lookup failed for {movie_id}: {e}")
        return frozenset()

def year_fits(result, year, language=None):
    """
    Filename year within +/- 1 of the TMDB year. Indian OTT rips are often named for their
    streaming year ("Kirkkan.2026" is the 2023 film), so a streaming/disc/TV release in the
    filename year counts too, as long as the film's language fits the filename's.
    """
    res_year = (result.get("release_date") or "")[:4]
    if not year or not res_year.isdigit():
        return True
    if abs(int(year) - int(res_year)) <= 1:
        return True
    res_language = result.get("original_language")
    if language and res_language != language and not (language in INDIAN_LANGUAGES and res_language in INDIAN_LANGUAGES):
        return False  # "Cup.2026.Malayalam" is not a 2020 English short with a 2025 festival run
    return any(y.isdigit() and abs(int(year) - int(y)) <= 1 for y in release_years(result["id"]))

def pick_best(title, year, results, strict, language=None, lookup_alternatives=False):
    """
    Best scoring result above the threshold whose year fits (exact match only when strict), or None.
    Films in the filename's language get a small bonus.
    """
    scored = []
    for rank, res in enumerate(results):
        score = title_score(title, res)
        if score < MIN_SIMILARITY and lookup_alternatives and rank < ALT_TITLE_LOOKUPS and res.get("id"):
            if not language or res.get("original_language") == language:
                score = title_score(title, res, alternative_titles(res["id"]))
        if score < (1.0 if strict else MIN_SIMILARITY):
            continue
        if not year_fits(res, year, language):
            logger.info(f"Year mismatch for '{title}': filename {year} vs TMDB {res.get('release_date')} ({res.get('title')})")
            continue
        if year and (res.get("release_date") or "")[:4] == str(year):
            score += YEAR_BONUS
        if language and res.get("original_language") == language:
            score += LANGUAGE_BONUS
        elif language in INDIAN_LANGUAGES and res.get("original_language") in INDIAN_LANGUAGES:
            score += REGIONAL_BONUS  # a Kannada film dubbed into Malayalam over a Hollywood namesake
        scored.append((score, res))

    # Ties go to the earlier (more popular) TMDB result
    return max(scored, key=lambda pair: pair[0])[1] if scored else None

def filename_titles(filename, guess):
    """
    Titles to search for, best first: guessit's title, then the text before the year when guessit
    dropped words ("V1 Murder Case", "Dil Se") or took a language word as the title ("Spa (2026) Malayalam").
    """
    titles = []
    guessed = (guess.get("title") or "").strip()
    if guessed and LANGUAGE_WORDS.sub("", guessed).strip(" -._"):
        titles.append(guessed)

    year = guess.get("year")
    stem = os.path.splitext(clean_filename(filename))[0]
    match = re.search(rf"(?<![0-9]){year}(?![0-9])", stem) if year else None
    if match:
        prefix = re.sub(r"\[[^\]]*\]", " ", stem[:match.start()])  # "[TamilMV] Title (2026)"
        prefix = LANGUAGE_WORDS.sub(" ", re.sub(r"[._]+", " ", prefix))
        prefix = re.sub(r"\s+", " ", prefix).strip(" -([")
        if prefix and normalize_title(prefix) not in (normalize_title(t) for t in titles):
            titles.append(prefix)
    return titles

def test_tmdb_api(api_key):
    """
    Tests if a TMDB API key is valid.
    """
    if not api_key:
        return False, "API Key is empty"
    
    try:
        tmdb.API_KEY = api_key
        # Attempt to get configuration - very lightweight call
        config = tmdb.Configuration()
        info = config.info()
        if 'images' in info:
            return True, "API Key is valid"
        return False, "Invalid response from TMDB"
    except Exception as e:
        logger.error(f"TMDB validation failed: {e}")
        return False, str(e)

def find_movie(search, title, year, language):
    """Search with the year, then without it; then check TMDB's alternative titles for those results."""
    # Short titles ("Gu", "Cup", "Haal") are easy to mis-match, so they need an exact title match
    strict = len(normalize_title(title).replace(" ", "")) < SHORT_TITLE_LENGTH

    with_year = search.movie(query=title, year=year).get('results', []) if year else []
    best = pick_best(title, year, with_year, strict, language)
    if best:
        return best

    logger.info(f"Low confidence or no result for '{title}' with year {year}. Retrying without year.")
    without_year = search.movie(query=title).get('results', [])
    best = pick_best(title, year, without_year, strict, language)
    if best:
        return best

    # TMDB search also matches alternative titles ("Daayam" finds "Inheritance"), so look at those
    for results in (with_year, without_year):
        best = pick_best(title, year, results, strict, language, lookup_alternatives=True)
        if best:
            return best
    return None

def get_movie_metadata(filename, pre_guess=None):
    tmdb_key = config_service.get_setting("TMDB_API_KEY")
    if tmdb_key:
        tmdb.API_KEY = tmdb_key
    guess = pre_guess or guessit(clean_filename(filename))
    year = guess.get('year')
    titles = filename_titles(filename, guess)

    if not titles:
        return None

    language = TMDB_LANGUAGES.get(extract_filename_language(clean_filename(filename)))

    try:
        search = tmdb.Search()
        for title in titles:
            best_match = find_movie(search, title, year, language)
            if not best_match:
                continue

            tmdb_year_str = best_match.get('release_date', '')[:4]
            final_year = tmdb_year_str if tmdb_year_str else str(year)

            # 1-year tolerance: if filename year is +/- 1 from TMDB, use filename year
            if year and tmdb_year_str.isdigit():
                tmdb_year_int = int(tmdb_year_str)
                if abs(year - tmdb_year_int) == 1:
                    logger.info(f"1-year discrepancy detected for '{best_match['title']}' ({tmdb_year_str} vs {year}). Preferring filename year.")
                    final_year = str(year)

            return {
                'title': best_match['title'],
                'year': final_year,
                'tmdb_id': best_match['id'],
                'overview': best_match.get('overview'),
                'poster_path': best_match.get('poster_path'),
                'original_language': best_match.get('original_language', 'und')
            }

    except Exception as e:
        logger.error(f"TMDB lookup failed for {filename}: {e}")

    # Fallback to guessit info if TMDB fails or no good result
    return {
        'title': titles[0],
        'year': str(year) if year else "Unknown",
        'tmdb_id': None
    }
