import datetime
from unittest.mock import patch

import pytest

from backend.core import processor
from backend.core.tv import parse_episode, pick_best_show, decide_episode, episode_label, search_titles

CONFIG = {
    "TV_DIR": "/media/tv-shows",
    "MALAYALAM_TV_DIR": "/media/tv-shows/malayalam-tv-shows",
}


@pytest.mark.parametrize("name,title,season,episode,date", [
    ("Bigg.Boss.Malayalam.S06E45.1080p.HS.WEB-DL.mkv", "Bigg Boss Malayalam", 6, 45, None),
    ("Uppum Mulakum Ep 123 720p.mp4", "Uppum Mulakum", None, 123, None),
    ("Santhwanam.Episode.1045.HDRip.mkv", "Santhwanam", None, 1045, None),
    ("Neeyum Naanum Epi 45.mkv", "Neeyum Naanum", None, 45, None),
    ("Kumkumapuvu 15-06-2023 Full Episode.mp4", "Kumkumapuvu", None, None, datetime.date(2023, 6, 15)),
    ("Kudumbavilakku 12th June 2024.mkv", "Kudumbavilakku", None, None, datetime.date(2024, 6, 12)),
    ("Panchayat.S03.E05.Hindi.720p.mkv", "Panchayat", 3, 5, None),
])
def test_parse_episode(name, title, season, episode, date):
    guess = parse_episode(name)
    assert guess is not None
    assert guess["title"] == title
    assert guess.get("season") == season
    assert guess.get("episode") == episode
    assert guess.get("date") == date


@pytest.mark.parametrize("name", [
    "Premam.2015.1080p.mkv",
    "Drishyam 2 2022 1080p.mkv",
    "Ponniyin.Selvan.Part.1.2022.mkv",
    "2018.2023.Malayalam.1080p.mkv",
    "Sacred.Games.S02.Complete.mkv",  # season pack, no episode number
])
def test_movies_are_not_episodes(name):
    assert parse_episode(name) is None


def test_episode_labels():
    assert episode_label({"season": 2, "episode": 3}) == "S02E03"
    assert episode_label({"episode": 123}) == "S01E123"
    assert episode_label({"season": 1, "episode": [1, 2]}) == "S01E01-E02"
    assert episode_label({"date": datetime.date(2024, 6, 12)}) == "2024-06-12"


def test_search_titles_drops_language_word():
    assert search_titles("Bigg Boss Malayalam") == ["Bigg Boss Malayalam", "Bigg Boss"]
    assert search_titles("Panchayat") == ["Panchayat"]


def test_pick_best_show_prefers_indian():
    results = [
        {"id": 1, "name": "Bigg Boss", "origin_country": ["US"]},
        {"id": 2, "name": "Bigg Boss", "origin_country": ["IN"]},
    ]
    assert pick_best_show("Bigg Boss", results, strict=False)["id"] == 2


def test_pick_best_show_rejects_weak_match():
    results = [{"id": 1, "name": "Something Else Entirely", "origin_country": ["IN"]}]
    assert pick_best_show("Uppum Mulakum", results, strict=False) is None


@patch("backend.core.tv.config_service")
def test_decide_episode_paths(mock_config):
    mock_config.get_all_settings.return_value = CONFIG
    show = {"title": "Kerala Crime Files", "year": "2023"}

    d = decide_episode("/in/Kerala.Crime.Files.S02E03.1080p.WEB-DL.MKV", "mal", {"season": 2, "episode": 3}, show)
    assert d.destination == (
        "/media/tv-shows/malayalam-tv-shows/Kerala Crime Files (2023)/Season 02/"
        "Kerala Crime Files - S02E03 1080p WEB-DL.mkv"
    )

    d = decide_episode("/in/x.mp4", "hin", {"date": datetime.date(2024, 6, 12)}, {"title": "Anupamaa", "year": "2020"})
    assert d.destination == "/media/tv-shows/Anupamaa (2020)/Season 2024/Anupamaa - 2024-06-12.mp4"


def test_process_file_routes_episode(tmp_path):
    src = tmp_path / "in" / "Uppum Mulakum Ep 123 720p.mp4"
    src.parent.mkdir()
    src.write_bytes(b"x")
    tv_dir = tmp_path / "tv"
    show = {"title": "Uppum Mulakum", "year": "2015", "tmdb_id": 1, "original_language": "ml", "indian": True}

    with patch("backend.core.processor.MIN_EPISODE_SIZE_BYTES", 0), \
         patch("backend.core.processor.get_show_metadata", return_value=show), \
         patch("backend.core.processor.get_quality_score", return_value=50), \
         patch("backend.core.language.detect_language", return_value="und"), \
         patch("backend.core.tv.config_service") as mock_config:
        mock_config.get_all_settings.return_value = {"TV_DIR": str(tv_dir), "MALAYALAM_TV_DIR": str(tv_dir / "mal")}
        result = processor.process_file(str(src))

    assert result["status"] == "processed"
    assert (tv_dir / "mal" / "Uppum Mulakum (2015)" / "Season 01" / "Uppum Mulakum - S01E123 720p.mp4").exists()
    assert not src.exists()


def test_process_file_skips_unknown_show(tmp_path):
    src = tmp_path / "Unknown Serial Ep 5.mkv"
    src.write_bytes(b"x")
    with patch("backend.core.processor.MIN_EPISODE_SIZE_BYTES", 0), \
         patch("backend.core.processor.get_show_metadata", return_value=None):
        result = processor.process_file(str(src))
    assert result["status"] == "skipped"
    assert src.exists()
