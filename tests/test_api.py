from fastapi.testclient import TestClient
import pytest

from backend.main import app

client = TestClient(app)


@pytest.mark.parametrize("origin", ["/media/../etc", "/mediafoo/x", "/etc"])
def test_cleanup_rejects_paths_outside_media(origin):
    r = client.post("/api/cleanup/start", json={
        "origin_dir": origin, "malayalam_dest": "/media/mal", "english_dest": "/media/eng",
    })
    assert "error" in r.json()


def test_dump_config_masks_tmdb_key(monkeypatch):
    from backend.core.config_service import config_service
    monkeypatch.setattr(config_service, "get_all_settings", lambda: {"TMDB_API_KEY": "abcdef123456"})
    assert client.get("/api/debug/dump_config").json()["TMDB_API_KEY"] == "****3456"


def test_ignore_patterns_endpoint_shape():
    assert "patterns" in client.get("/api/ignore/patterns").json()


def test_head_root_is_allowed():
    assert client.head("/").status_code == 200


def test_health():
    assert client.get("/health").json()["status"] == "ok"


@pytest.mark.parametrize("page", ["/", "/cleanup", "/monitoring", "/settings"])  # /monitoring redirects to /
def test_pages_render(page):
    assert client.get(page).status_code == 200


def test_rescan_skipped_requires_running_watcher():
    assert client.post("/api/monitoring/watcher/rescan-skipped").status_code == 409
