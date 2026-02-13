import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.core.file_ops import apply_permissions, move_file

class TestPermissions(unittest.TestCase):

    @patch('os.getenv')
    @patch('os.chown', create=True)
    @patch('os.chmod', create=True)
    @patch('os.name', 'posix') # Force posix to test chown logic
    def test_apply_permissions(self, mock_chmod, mock_chown, mock_getenv):
        mock_getenv.side_effect = lambda k: "1001" if k == "PUID" or k == "PGID" else None
        
        with patch('os.path.isdir', return_value=True):
            apply_permissions("/test/dir")
            mock_chown.assert_called_with("/test/dir", 1001, 1001)
            mock_chmod.assert_called_with("/test/dir", 0o775)

    @patch('shutil.move')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('backend.core.file_ops.apply_permissions')
    def test_move_file_permissions(self, mock_apply, mock_makedirs, mock_exists, mock_move):
        # Setup mocks
        mock_exists.side_effect = lambda p: True if p == "src" else False
        
        move_file("src", "/dest/dir/file.mkv")
        
        # Verify makedirs was called for dest_dir
        mock_makedirs.assert_called_once_with("/dest/dir", exist_ok=True)
        # Verify apply_permissions called for both dir and file
        self.assertEqual(mock_apply.call_count, 2)
        mock_apply.assert_any_call("/dest/dir")
        mock_apply.assert_any_call("/dest/dir/file.mkv")

if __name__ == '__main__':
    unittest.main()
