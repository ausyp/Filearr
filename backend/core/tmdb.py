import tmdbsimple as tmdb
from guessit import guessit
from backend.core.config_service import config_service
import logging
import difflib

logger = logging.getLogger(__name__)

def is_similar(str1, str2):
    """
    Checks if two strings are similar using SequenceMatcher.
    """
    if not str1 or not str2:
        return 0.0
    return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

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

def get_movie_metadata(filename):
    tmdb_key = config_service.get_setting("TMDB_API_KEY")
    if tmdb_key:
        tmdb.API_KEY = tmdb_key
    guess = guessit(filename)
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
            if similarity > 0.8:
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
                
                # Final check: if even the best match is poor, we might want to discard it
                if best_similarity < 0.6:
                    logger.warning(f"Best match for '{title}' has low similarity ({best_similarity:.2f}): {best_match['title']}")
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
