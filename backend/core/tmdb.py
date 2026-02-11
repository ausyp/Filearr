import tmdbsimple as tmdb
from guessit import guessit
from backend.core.config_service import config_service
import logging

logger = logging.getLogger(__name__)

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
        response = search.movie(query=title, year=year)
        if response['results']:
            # Return first result
            result = response['results'][0]
            return {
                'title': result['title'],
                'year': result['release_date'][:4] if result.get('release_date') else year,
                'tmdb_id': result['id'],
                'overview': result['overview'],
                'poster_path': result['poster_path'],
                'original_language': result.get('original_language', 'und')
            }
    except Exception as e:
        logger.error(f"TMDB lookup failed for {filename}: {e}")
        
    # Fallback to guessit info if TMDB fails or no key
    return {
        'title': title,
        'year': str(year) if year else "Unknown",
        'tmdb_id': None
    }
