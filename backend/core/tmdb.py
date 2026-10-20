import tmdbsimple as tmdb
from guessit import guessit
from backend.core.config_service import config_service
import logging
import difflib
import re
import unicodedata

logger = logging.getLogger(__name__)

MIN_SIMILARITY = 0.7
SHORT_TITLE_LENGTH = 6  # titles shorter than this need an exact TMDB match
TOKEN_MATCH_RATIO = 0.85  # "kaandam" ~ "kandam", "terminator" ~ "terminators"

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

def title_score(title, result):
    """Best similarity against the TMDB title, original title, and the title before a subtitle colon."""
    candidates = [result.get("title"), result.get("original_title")]
    candidates += [c.split(":")[0] for c in candidates if c and ":" in c]  # "Pushpa 2" vs "Pushpa 2: The Rule"
    return max((is_similar(title, c) for c in candidates if c), default=0.0)

def pick_best(title, year, results, strict):
    """Best scoring result above the threshold (exact match only when strict), or None."""
    best, best_score = None, 0.0
    for res in results:
        score = title_score(title, res)
        if strict and score < 1.0:
            continue
        res_year = (res.get("release_date") or "")[:4]
        if year and res_year == str(year):
            score += 0.1
        if score > best_score:
            best, best_score = res, score
    if best is not None and best_score < MIN_SIMILARITY:
        logger.warning(f"Best match for '{title}' has low similarity ({best_score:.2f}): {best.get('title')}")
        return None
    return best

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

def get_movie_metadata(filename, pre_guess=None):
    tmdb_key = config_service.get_setting("TMDB_API_KEY")
    if tmdb_key:
        tmdb.API_KEY = tmdb_key
    guess = pre_guess or guessit(filename)
    title = guess.get('title')
    year = guess.get('year')
    
    if not title:
        return None
        
    try:
        search = tmdb.Search()
        
        # Short titles ("Gu", "Cup", "Haal") are easy to mis-match, so they need an exact title match
        strict = len(normalize_title(title).replace(" ", "")) < SHORT_TITLE_LENGTH

        # 1. Try search with year, then 2. without year if nothing good comes back
        results = search.movie(query=title, year=year).get('results', []) if year else []
        best_match = pick_best(title, year, results, strict)
        if not best_match:
            logger.info(f"Low confidence or no result for '{title}' with year {year}. Retrying without year.")
            results = search.movie(query=title).get('results', [])
            best_match = pick_best(title, year, results, strict)

        if best_match:
            # Strict year lock: when filename has a year, TMDB year must be within +/- 1.
            tmdb_year_str = best_match.get('release_date', '')[:4]
            if year and tmdb_year_str.isdigit() and abs(int(year) - int(tmdb_year_str)) > 1:
                logger.warning(
                    f"Year mismatch for '{title}': filename {year} vs TMDB {tmdb_year_str}. Skipping match."
                )
                best_match = None

        if best_match:
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
        'title': title,
        'year': str(year) if year else "Unknown",
        'tmdb_id': None
    }
