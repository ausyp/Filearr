import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.core.decision import decide


class TestDecisionFileNaming(unittest.TestCase):

    @patch('backend.core.decision.config_service')
    def test_preserves_quality_tags_in_filename(self, mock_config):
        mock_config.get_all_settings.return_value = {
            "MOVIES_DIR": "/media/movies",
            "MALAYALAM_DIR": "/media/movies/malayalam",
            "REJECTED_DIR": "/media/movies/.rejected",
        }

        result = decide(
            file_path="/downloads/The.Matrix.1999.1080p.BluRay.x265.mkv",
            language="eng",
            quality_score=80,
            is_cam=False,
            tmdb_info={"title": "The Matrix", "year": "1999"},
        )

        self.assertIn("The Matrix (1999) 1080P BLURAY X265.mkv", result.destination)

    @patch('backend.core.decision.config_service')
    def test_no_tags_still_uses_clean_name(self, mock_config):
        mock_config.get_all_settings.return_value = {"MOVIES_DIR": "/media/movies"}

        result = decide(
            file_path="/downloads/Casablanca.1942.mkv",
            language="eng",
            quality_score=80,
            is_cam=False,
            tmdb_info={"title": "Casablanca", "year": "1942"},
        )

        self.assertTrue(result.destination.endswith("/Casablanca (1942)/Casablanca (1942).mkv"))


if __name__ == '__main__':
    unittest.main()
