import tmdbsimple as tmdb
from guessit import guessit
from backend.core.config_service import config_service
import logging
import difflib
import re

logger = logging.getLogger(__name__)

def is_similar(str1, str2):
    """Conservative similarity scorer to reduce catastrophic false positives."""
    if not str1 or not str2:
        return 0.0

    s1 = str1.lower().strip()
    s2 = str2.lower().strip()

    seq_ratio = difflib.SequenceMatcher(None, s1, s2).ratio()

    # Handle joined-vs-split titles: "Babygirl" vs "Baby Girl".
    if re.sub(r'[^a-z0-9]+', '', s1) == re.sub(r'[^a-z0-9]+', '', s2):
        return max(seq_ratio, 0.95)

    tokens1 = [t for t in re.split(r"[^a-z0-9]+", s1) if t]
    tokens2 = [t for t in re.split(r"[^a-z0-9]+", s2) if t]
    if not tokens1 or not tokens2:
        return seq_ratio

    # For single-token titles (Arya vs Aryan), require exact token equality.
    if len(tokens1) == 1 and len(tokens2) == 1:
        return 1.0 if tokens1[0] == tokens2[0] else 0.0

    set1, set2 = set(tokens1), set(tokens2)
    overlap = len(set1 & set2) / max(len(set1), len(set2))

    # Prevent "Terminator 2" matching "Angel Terminators 2".
    if tokens1[0] != tokens2[0] and overlap < 0.8:
        return min(overlap, seq_ratio * 0.6)

    # Keep score conservative: both overlap and sequence should be decent.
    return (overlap * 0.7) + (seq_ratio * 0.3)

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
        
        # 1. Try search with year
        response = search.movie(query=title, year=year)
        results = response.get('results', [])
        
        best_match = None
        
        if results:
            first_result = results[0]
            similarity = is_similar(title, first_result['title'])
            
            # If high confidence, use it
            if similarity >= 0.72:
                best_match = first_result
        
        # 2. Fallback search without year if no results or low similarity
        if not best_match:
            logger.info(f"Low confidence or no result for '{title}' with year {year}. Retrying without year.")
            response = search.movie(query=title)
            results = response.get('results', [])
            
            if results:
                # Find the best match among results
                best_similarity = 0
                for res in results:
                    sim = is_similar(title, res['title'])
                    
                    # Boost similarity if year matches
                    res_year = res.get('release_date', '')[:4]
                    if str(year) == res_year:
                        sim += 0.1
                    
                    if sim > best_similarity:
                        best_similarity = sim
                        best_match = res
                
                # Final check: reject low-confidence matches
                if best_similarity < 0.72:
                    logger.warning(f"Best match for '{title}' has low similarity ({best_similarity:.2f}): {best_match['title']}")
                    best_match = None

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
                'overview': best_match['overview'],
                'poster_path': best_match['poster_path'],
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
