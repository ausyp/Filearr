import tmdbsimple as tmdb
import os
from backend.core.config_service import config_service
import json

def test_raid():
    # Point to the local data directory where filearr.db is
    os.environ["DATA_DIR"] = "data"
    tmdb_key = config_service.get_setting("TMDB_API_KEY")
    if not tmdb_key:
        print("No TMDB API KEY found")
        return
    tmdb.API_KEY = tmdb_key
    
    search = tmdb.Search()
    
    print("--- Search: 'The Raid Redemption' with year 2011 ---")
    response_2011 = search.movie(query='The Raid Redemption', year=2011)
    results_2011 = response_2011.get('results', [])
    for res in results_2011[:3]:
        print(f"ID: {res['id']}, Title: {res['title']}, Release: {res.get('release_date')}")

    print("\n--- Search: 'The Raid Redemption' with year 2012 ---")
    response_2012 = search.movie(query='The Raid Redemption', year=2012)
    results_2012 = response_2012.get('results', [])
    for res in results_2012[:3]:
        print(f"ID: {res['id']}, Title: {res['title']}, Release: {res.get('release_date')}")

    print("\n--- Search: 'The Raid Redemption' (no year) ---")
    response_none = search.movie(query='The Raid Redemption')
    results_none = response_none.get('results', [])
    for res in results_none[:5]:
        print(f"ID: {res['id']}, Title: {res['title']}, Release: {res.get('release_date')}")

if __name__ == "__main__":
    test_raid()
