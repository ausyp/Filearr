import os
import tempfile
import unittest
from unittest.mock import patch

from backend.core.safety import evaluate_safety, extract_filename_language
from backend.core.language import get_refined_language


class TestSafety(unittest.TestCase):
    def test_sample_file_is_rejected(self):
        fd, sample_path = tempfile.mkstemp(suffix='.Sample.mkv')
        os.close(fd)
        try:
            allowed, reason, _ = evaluate_safety(sample_path)
            self.assertFalse(allowed)
            self.assertEqual(reason, "Sample file")
        finally:
            os.unlink(sample_path)

    def test_small_file_is_rejected(self):
        with tempfile.NamedTemporaryFile(suffix=".mkv") as f:
            f.write(b"x" * 1024)
            f.flush()
            with patch('backend.core.safety.guessit', return_value={'title': 'Some Movie', 'year': 2020}):
                allowed, reason, _ = evaluate_safety(f.name)
            self.assertFalse(allowed)
            self.assertEqual(reason, "Too small to be full movie")

    @patch('backend.core.safety.os.path.getsize', return_value=400 * 1024 * 1024)
    def test_no_year_rejected(self, _):
        with patch('backend.core.safety.guessit', return_value={'title': 'Random Stuff'}):
            allowed, reason, _ = evaluate_safety('/tmp/Random.Stuff.mkv')
        self.assertFalse(allowed)
        self.assertEqual(reason, "No year in filename")

    @patch('backend.core.safety.os.path.getsize', return_value=400 * 1024 * 1024)
    def test_short_title_rejected(self, _):
        with patch('backend.core.safety.guessit', return_value={'title': 'ETRG', 'year': 2020}):
            allowed, reason, _ = evaluate_safety('/tmp/ETRG.2020.mkv')
        self.assertFalse(allowed)
        self.assertEqual(reason, "Suspicious short title")

    @patch('backend.core.language.detect_language', return_value='eng')
    def test_filename_language_priority(self, _):
        filename_lang = extract_filename_language('Businessman.Tamil.2012.mkv')
        lang = get_refined_language('/tmp/Businessman.Tamil.2012.mkv', {'original_language': 'en'}, filename_lang=filename_lang)
        self.assertEqual(lang, 'tam')


if __name__ == '__main__':
    unittest.main()
