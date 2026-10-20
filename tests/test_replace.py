from unittest.mock import patch

from backend.core import processor
from backend.core.decision import Decision


def setup_library(tmp_path, *names):
    folder = tmp_path / "lib"
    folder.mkdir()
    for name in names:
        (folder / name).write_bytes(b"old")
    src = tmp_path / "in" / "new.mkv"
    src.parent.mkdir()
    src.write_bytes(b"new")
    return folder, src


def run(src, decision, rejected):
    with patch("backend.core.file_ops.config_service") as mock_config:
        mock_config.get_all_settings.return_value = {"REJECTED_DIR": str(rejected)}
        return processor.execute_move(str(src), decision, {"title": "X", "year": "2015"}, "mal", 50)


def test_new_download_replaces_other_quality_of_same_movie(tmp_path):
    folder, src = setup_library(tmp_path, "Premam (2015) 720p.mkv", "Premam (2015) 720p.srt")
    decision = Decision(action="move", destination=str(folder / "Premam (2015) 1080p.mkv"),
                        reason="", same_item_prefix="Premam (2015)")
    result = run(src, decision, tmp_path / "rejected")

    assert result["status"] == "processed"
    assert "replacing Premam (2015) 720p.mkv" in result["reason"]
    assert (folder / "Premam (2015) 1080p.mkv").read_bytes() == b"new"
    assert not (folder / "Premam (2015) 720p.mkv").exists()
    assert (tmp_path / "rejected" / "Premam (2015) 720p.mkv").exists()
    assert (folder / "Premam (2015) 720p.srt").exists()  # not a video


def test_new_download_replaces_file_with_same_name(tmp_path):
    folder, src = setup_library(tmp_path, "Premam (2015).mkv")
    decision = Decision(action="move", destination=str(folder / "Premam (2015).mkv"),
                        reason="", same_item_prefix="Premam (2015)")
    result = run(src, decision, tmp_path / "rejected")

    assert result["status"] == "processed"
    assert (folder / "Premam (2015).mkv").read_bytes() == b"new"
    assert (tmp_path / "rejected" / "Premam (2015).mkv").read_bytes() == b"old"


def test_other_episodes_are_left_alone(tmp_path):
    folder, src = setup_library(
        tmp_path,
        "Show - S01E05 480p.mp4",
        "Show - S01E050.mp4",
        "Show - S01E05-E06.mp4",
        "Show - S01E06.mp4",
    )
    decision = Decision(action="move", destination=str(folder / "Show - S01E05 720p.mkv"),
                        reason="", same_item_prefix="Show - S01E05")
    run(src, decision, tmp_path / "rejected")

    assert sorted(p.name for p in folder.iterdir()) == [
        "Show - S01E05 720p.mkv", "Show - S01E05-E06.mp4", "Show - S01E050.mp4", "Show - S01E06.mp4",
    ]
    assert [p.name for p in (tmp_path / "rejected").iterdir()] == ["Show - S01E05 480p.mp4"]
