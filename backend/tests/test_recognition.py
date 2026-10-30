import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.core import tmdb as tmdb_module
from backend.core.tmdb import get_movie_metadata, is_similar, filename_titles

def movie(id, title, date, language='en', original_title=None):
    return {'id': id, 'title': title, 'original_title': original_title or title, 'release_date': date,
            'original_language': language, 'overview': '', 'poster_path': ''}

class TestRecognition(unittest.TestCase):

    def setUp(self):
        tmdb_module._alternative_titles.cache_clear()
        tmdb_module._release_years.cache_clear()
        # No real TMDB calls: films have no alternative titles or later releases unless a test says so
        patcher = patch('backend.core.tmdb.tmdb.Movies')
        self.mock_movies = patcher.start()
        self.addCleanup(patcher.stop)
        self.set_tmdb_extras({}, {})

    def set_tmdb_extras(self, alt_titles, release_dates):
        """alt_titles: {id: [title]}, release_dates: {id: [(date, type)]}"""
        def movies(movie_id):
            m = MagicMock()
            m.alternative_titles.return_value = {'titles': [{'title': t} for t in alt_titles.get(movie_id, [])]}
            m.release_dates.return_value = {'results': [{'iso_3166_1': 'IN', 'release_dates': [
                {'release_date': f"{d}T00:00:00.000Z", 'type': t} for d, t in release_dates.get(movie_id, [])]}]}
            return m
        self.mock_movies.side_effect = movies

    def test_similarity(self):
        self.assertGreater(is_similar("Baby Girl", "Babygirl"), 0.8)
        self.assertGreater(is_similar("Baby Girl", "Baby Girl"), 0.9)
        self.assertLess(is_similar("Baby Girl", "Sugar Baby"), 0.6)

    def test_similarity_strict_single_token(self):
        self.assertEqual(is_similar("Arya", "Aryan"), 0.0)

    def test_similarity_reduces_prefix_mismatch(self):
        self.assertLess(is_similar("Terminator 2", "Angel Terminators 2"), 0.7)

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
        
        result = get_movie_metadata("The.Raid.2011.1080p.mkv")
        
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
        
        # Strict year lock should reject this TMDB match and fall back to guessed metadata
        self.assertEqual(result['year'], "2020")
        self.assertIsNone(result['tmdb_id'])

    def test_similarity_variants(self):
        self.assertGreaterEqual(is_similar("Kishkindha Kaandam", "Kishkindha Kandam"), 0.7)
        self.assertEqual(is_similar("Fast & Furious", "Fast and Furious"), 1.0)
        self.assertEqual(is_similar("The Raid", "Raid"), 1.0)

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_short_title_needs_exact_match(self, mock_config, mock_search):
        mock_config.get_setting.return_value = "fake_key"
        instance = mock_search.return_value
        instance.movie.return_value = {'results': [
            {'title': 'Guru', 'release_date': '2024-01-01', 'id': 1, 'overview': '', 'poster_path': ''},
            {'title': 'Gu', 'release_date': '2024-02-01', 'id': 2, 'overview': '', 'poster_path': '', 'original_language': 'ml'},
        ]}
        result = get_movie_metadata("Gu.2024.Malayalam.1080p.mkv")
        self.assertEqual(result['tmdb_id'], 2)

        instance.movie.return_value = {'results': [
            {'title': 'Guru', 'release_date': '2024-01-01', 'id': 1, 'overview': '', 'poster_path': ''},
        ]}
        self.assertIsNone(get_movie_metadata("Gu.2024.Malayalam.1080p.mkv")['tmdb_id'])

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_best_result_not_just_first(self, mock_config, mock_search):
        mock_config.get_setting.return_value = "fake_key"
        instance = mock_search.return_value
        instance.movie.return_value = {'results': [
            {'title': 'Pushpa: The Rise', 'release_date': '2021-12-17', 'id': 1, 'overview': '', 'poster_path': ''},
            {'title': 'Pushpa 2: The Rule', 'release_date': '2024-12-05', 'id': 2, 'overview': '', 'poster_path': ''},
        ]}
        result = get_movie_metadata("Pushpa.2.2024.1080p.mkv")
        self.assertEqual(result['tmdb_id'], 2)
        self.assertEqual(instance.movie.call_count, 1)

    def test_filename_titles(self):
        from guessit import guessit
        def titles(name):
            return filename_titles(name, guessit(name))
        # guessit drops "V1" and "Se"; the text before the year keeps them
        self.assertEqual(titles("V1 Murder Case (2021) Multi Audio 1080p HEVC.mkv"), ["Murder Case", "V1 Murder Case"])
        self.assertEqual(titles("Dil.Se.1998.1080p.NF.WEB-DL.DDP5.1.AV1-Saon.mkv"), ["Dil", "Dil Se"])
        # "Spa" reads as Spanish to guessit, which then takes "Malayalam" for the title
        self.assertEqual(titles("Spa (2026) Malayalam HQ HDRip - 1080p - x264.mkv"), ["Spa"])
        self.assertEqual(titles("Baby Girl (2026) Malayalam.mkv"), ["Baby Girl"])

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_text_before_year_is_searched(self, mock_config, mock_search):
        mock_config.get_setting.return_value = "fake_key"
        def search(query, year=None):
            if query == "Dil Se":
                return {'results': [movie(21210, 'Dil Se..', '1998-08-21', 'hi')]}
            return {'results': [movie(65683, 'Dil', '1990-06-22', 'hi')]}
        mock_search.return_value.movie.side_effect = search
        result = get_movie_metadata("Dil.Se.1998.1080p.NF.WEB-DL.DDP5.1.AV1-Saon.mkv")
        self.assertEqual((result['title'], result['tmdb_id']), ('Dil Se..', 21210))

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_non_breaking_space_in_filename(self, mock_config, mock_search):
        mock_config.get_setting.return_value = "fake_key"
        mock_search.return_value.movie.return_value = {'results': [movie(1516501, 'Prathichaya', '2026-03-01', 'ml')]}
        result = get_movie_metadata("_Prathichaya_2026\xa0Malayalam_HQ_HDRip_1080p_x264_DD+5_1.mkv")
        self.assertEqual(result['tmdb_id'], 1516501)

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_numbered_list_prefix(self, mock_config, mock_search):
        mock_config.get_setting.return_value = "fake_key"
        def search(query, year=None):
            if query == "Apocalypse Z New World":
                return {'results': [movie(1, 'Apocalypse Z: New World', '2026-10-24', 'es')]}
            if query == "Comrade Kalyan":
                return {'results': [movie(2, 'Comrade Kalyan', '2026-09-12', 'ml')]}
            return {'results': [movie(3, query, '2026-01-01', 'en')]}
        mock_search.return_value.movie.side_effect = search
        result = get_movie_metadata("1970 - Apocalypse.Z.New.World.2026.1080p.AMZN.WEB-DL.DUAL.DDP5..mkv")
        self.assertEqual((result['title'], result['tmdb_id']), ('Apocalypse Z: New World', 1))
        result = get_movie_metadata("1968 - Comrade.Kalyan.2026.Malayalam.1080p.AMZN.WEB-DL.DD+5.1.H.mkv")
        self.assertEqual((result['title'], result['tmdb_id']), ('Comrade Kalyan', 2))

    def test_numbered_prefix_kept_when_it_is_the_title(self):
        from backend.core.safety import clean_filename
        self.assertEqual(clean_filename("1917 - 2019 1080p.mkv"), "1917 - 2019 1080p.mkv")
        self.assertEqual(clean_filename("1917.2019.1080p.mkv"), "1917.2019.1080p.mkv")
        self.assertEqual(clean_filename("1986 - Malayalam.2024.mkv"), "1986 - Malayalam.2024.mkv")
        self.assertEqual(clean_filename("1968 - Comrade.Kalyan.2026.mkv"), "Comrade.Kalyan.2026.mkv")

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_ott_release_year(self, mock_config, mock_search):
        """Kirkkan.2026 is the 2023 film's streaming release"""
        mock_config.get_setting.return_value = "fake_key"
        mock_search.return_value.movie.return_value = {'results': [movie(1338801, 'Kirkkan', '2023-07-21', 'ml')]}
        self.set_tmdb_extras({}, {1338801: [('2023-07-21', 3), ('2026-01-15', 4)]})
        result = get_movie_metadata("Kirkkan.2026.1080p.SNXT.WEB-DL.Malayalam.DDP5.1.H264.mkv")
        self.assertEqual((result['tmdb_id'], result['year']), (1338801, '2023'))

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_later_release_needs_streaming_and_matching_language(self, mock_config, mock_search):
        mock_config.get_setting.return_value = "fake_key"
        mock_search.return_value.movie.return_value = {'results': [movie(1513973, 'The Cup', '2020-01-01', 'en')]}
        # A 2025 festival screening of an English short is not "Cup.2026.Malayalam"
        self.set_tmdb_extras({}, {1513973: [('2025-07-19', 3)]})
        self.assertIsNone(get_movie_metadata("Cup.2026.1080p.MMAX.WEB-DL.Malayalam.mkv")['tmdb_id'])
        tmdb_module._release_years.cache_clear()
        self.set_tmdb_extras({}, {1513973: [('2026-02-01', 4)]})
        self.assertIsNone(get_movie_metadata("Cup.2026.1080p.MMAX.WEB-DL.Malayalam.mkv")['tmdb_id'])

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_alternative_title(self, mock_config, mock_search):
        """TMDB lists Daayam as "Inheritance" with Daayam as an alternative title"""
        mock_config.get_setting.return_value = "fake_key"
        mock_search.return_value.movie.return_value = {'results': [movie(1151927, 'Inheritance', '2023-10-31', 'ml', 'ദായം')]}
        self.set_tmdb_extras({1151927: ['dhaayam', 'Daayam']}, {1151927: [('2026-07-11', 4)]})
        result = get_movie_metadata("Daayam.2026.1080p.MMAX.WEB-DL.Malayalam.DD5.1.H.265-.mkv")
        self.assertEqual((result['title'], result['tmdb_id']), ('Inheritance', 1151927))

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_alternative_titles_only_for_filename_language(self, mock_config, mock_search):
        mock_config.get_setting.return_value = "fake_key"
        mock_search.return_value.movie.return_value = {'results': [movie(5, 'Inheritance', '2026-01-01', 'en')]}
        self.set_tmdb_extras({5: ['Daayam']}, {})
        self.assertIsNone(get_movie_metadata("Daayam.2026.Malayalam.mkv")['tmdb_id'])

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_prefers_film_in_filename_language(self, mock_config, mock_search):
        mock_config.get_setting.return_value = "fake_key"
        mock_search.return_value.movie.return_value = {'results': [
            movie(1736527, 'Peter', '2026-08-11', 'en'),
            movie(1669824, 'Peter', '2026-04-10', 'kn', 'ಪೀಟರ್'),
        ]}
        result = get_movie_metadata("Peter (2026) HQ HDRip - x264 - [Tamil + Malayalam] -.mkv")
        self.assertEqual(result['tmdb_id'], 1669824)

    @patch('backend.core.tmdb.tmdb.Search')
    @patch('backend.core.tmdb.config_service')
    def test_year_bonus_does_not_lift_weak_title(self, mock_config, mock_search):
        """'Merry Christmas' is not 'Merry Christmas, Dude.' just because both are 2026"""
        mock_config.get_setting.return_value = "fake_key"
        mock_search.return_value.movie.return_value = {'results': [movie(1760937, 'Merry Christmas, Dude.', '2026-12-01')]}
        self.assertIsNone(get_movie_metadata("Merry Christmas (2026) Malayalam TRUE WEB-DL - 1080p.mkv")['tmdb_id'])

if __name__ == '__main__':
    unittest.main()
