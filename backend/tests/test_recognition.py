import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.core.tmdb import get_movie_metadata, is_similar

class TestRecognition(unittest.TestCase):

    def test_similarity(self):
        self.assertGreater(is_similar("Baby Girl", "Babygirl"), 0.8)
        self.assertGreater(is_similar("Baby Girl", "Baby Girl"), 0.9)
        self.assertLess(is_similar("Baby Girl", "Sugar Baby"), 0.6)

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_get_movie_metadata_fallback(self, mock_config, mock_search):
        mock_config.get_setting.return_value = "fake_key"
        
        # Setup the mock search instance
        instance = mock_search.return_value
        
        # Scenario: "Baby Girl (2025)"
        # 1. Search with year 2025 returns "Sugar Baby (2024)" (which might happen if TMDB is fuzzy)
        # OR it returns nothing for 2025.
        
        def mock_movie(query, year=None):
            if year == 2025:
                # Simulate no results or bad results for 2025
                return {'results': [{'title': 'Sugar Baby', 'release_date': '2024-01-01', 'id': 123, 'overview': '', 'poster_path': ''}]}
            else:
                # Simulate search without year returning the correct one
                return {'results': [
                    {'title': 'Baby Girl', 'release_date': '2026-01-23', 'id': 456, 'overview': 'Correct', 'poster_path': '', 'original_language': 'ml'},
                    {'title': 'Sugar Baby', 'release_date': '2024-01-01', 'id': 123, 'overview': '', 'poster_path': ''}
                ]}
        
        instance.movie.side_effect = mock_movie
        
        result = get_movie_metadata("Baby Girl (2025) Malayalam WEB-DL.mkv")
        
        self.assertEqual(result['title'], "Baby Girl")
        self.assertEqual(result['tmdb_id'], 456)
        self.assertEqual(result['original_language'], 'ml')

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_get_movie_metadata_high_confidence(self, mock_config, mock_search):
        mock_config.get_setting.return_value = "fake_key"
        instance = mock_search.return_value
        
        # Scenario: Search with year returns exact match immediately
        instance.movie.return_value = {'results': [
            {'title': 'Babygirl', 'release_date': '2024-12-25', 'id': 789, 'overview': 'Kidman', 'poster_path': ''}
        ]}
        
        result = get_movie_metadata("Babygirl (2024) 1080p.mkv")
        
        self.assertEqual(result['title'], "Babygirl")
        self.assertEqual(result['tmdb_id'], 789)
        # Should not have called movie() a second time
        self.assertEqual(instance.movie.call_count, 1)

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_year_tolerance(self, mock_config, mock_search):
        mock_config.get_setting.return_value = "fake_key"
        instance = mock_search.return_value
        
        # Scenario: Filename says 2011, TMDB says 2012
        # Title is a high-confidence match
        instance.movie.return_value = {'results': [
            {'title': 'The Raid', 'release_date': '2012-03-23', 'id': 9405, 'overview': 'SWAT', 'poster_path': ''}
        ]}
        
        result = get_movie_metadata("The.Raid.Redemption.2011.1080p.mkv")
        
        self.assertEqual(result['title'], "The Raid")
        self.assertEqual(result['year'], "2011") # Should use filename year because of 1-year tolerance
        self.assertEqual(result['tmdb_id'], 9405)

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_year_no_tolerance(self, mock_config, mock_search):
        mock_config.get_setting.return_value = "fake_key"
        instance = mock_search.return_value
        
        # Scenario: Filename says 2020, TMDB says 2015 (too much discrepancy)
        instance.movie.return_value = {'results': [
            {'title': 'Old Movie', 'release_date': '2015-01-01', 'id': 999, 'overview': 'Old', 'poster_path': ''}
        ]}
        
        result = get_movie_metadata("Old Movie (2020).mkv")
        
        # In this case, it might still return it if similarity is high enough, 
        # but it should use TMDB's year OR discard it if we implemented stricter checks.
        # Current implementation uses TMDB year if similarity > 0.8
        self.assertEqual(result['year'], "2015")

if __name__ == '__main__':
    unittest.main()
