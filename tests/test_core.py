import os

import pytest

from backend.config.settings import Settings
from backend.core.cam_detector import is_cam
from backend.core.decision import decide
from backend.core.file_ops import move_file, rejection_move
from backend.core.ignore_service import ignore_service
from backend.core.processor import is_media_file


def test_settings_derive_paths_from_env(monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", "/library")
    monkeypatch.setenv("DATA_DIR", "/state")
    s = Settings()
    assert s.DATABASE_URL == "sqlite:////state/filearr.db"
    assert s.REJECTED_DIR == "/library/rejected"
    assert s.MOVIES_DIR == "/library"
    assert s.MALAYALAM_DIR == "/library/malayalam-movies"
    assert s.TV_DIR == "/tv-shows"
    assert s.MALAYALAM_TV_DIR == "/tv-shows/malayalam-tv-shows"


@pytest.mark.parametrize("name,expected", [
    ("Movie.2023.HDCAM.x264.mkv", True),
    ("Movie 2023 TS 720p.mp4", True),
    ("Movie.2023.1080p.BluRay.ts", False),  # .ts container, not telesync
    ("Movie.2023.1080p.WEB-DL.DTS.mkv", False),
])
def test_is_cam(name, expected):
    assert is_cam(name) is expected


def test_is_media_file():
    assert is_media_file("/x/Movie.MKV")
    assert not is_media_file("/x/Movie.nfo")
    assert not is_media_file("/x/Movie.mkv.part")


def test_decide_builds_library_path(tmp_path):
    d = decide(
        "/in/some.release.name.MKV", "eng", 50, False,
        {"title": "Who: Framed?", "year": 1988},
        movies_dir_override=str(tmp_path),
    )
    assert d.action == "move"
    assert d.destination == os.path.join(str(tmp_path), "Who Framed (1988)", "Who Framed (1988).mkv")


def test_decide_routes_malayalam(tmp_path):
    d = decide("/in/a.mkv", "mal", 50, False, {"title": "Drishyam", "year": "2013"},
               movies_dir_override="/eng", mal_dir_override=str(tmp_path))
    assert d.destination.startswith(str(tmp_path))


def test_move_file_never_overwrites(tmp_path):
    src = tmp_path / "new.mkv"
    src.write_text("new")
    dest = tmp_path / "lib" / "movie.mkv"
    dest.parent.mkdir()
    dest.write_text("existing")
    assert move_file(str(src), str(dest)) is False
    assert dest.read_text() == "existing"
    assert src.exists()


def test_rejection_move_keeps_both_copies(tmp_path, monkeypatch):
    from backend.core import config_service as cs
    rejected = tmp_path / "rejected"
    monkeypatch.setattr(cs.config_service, "get_all_settings", lambda: {"REJECTED_DIR": str(rejected)})
    for content in ("first", "second"):
        f = tmp_path / "Movie.CAM.mkv"
        f.write_text(content)
        assert rejection_move(str(f), "cam")
    assert sorted(p.name for p in rejected.iterdir()) == ["Movie.CAM (1).mkv", "Movie.CAM.mkv"]


def test_default_ignore_patterns_apply_without_db_value():
    ignored, reason = ignore_service.should_ignore("/in/movie.sample")
    assert ignored and "*.sample" in reason
    assert ignore_service.should_ignore("/in/Movie.2020.mkv") == (False, "")
