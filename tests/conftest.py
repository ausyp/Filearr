import os
import sys
import tempfile

# Point the app at a throwaway data dir before any backend module is imported
_data_dir = tempfile.mkdtemp(prefix="filearr-test-")
os.environ["DATA_DIR"] = _data_dir
os.environ.setdefault("TMDB_API_KEY", "")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import models  # noqa: E402,F401  (register tables)
from backend.db.database import init_db  # noqa: E402

init_db()
