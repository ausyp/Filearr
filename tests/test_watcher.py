from backend.core.watcher import WatcherManager, log_watcher_event, MAX_FAILED_ATTEMPTS


def queued_paths(manager):
    items = []
    while not manager.queue.empty():
        items.append(manager.queue.get()[1])
    return items


def test_scan_queues_new_and_failed_but_not_skipped(tmp_path):
    new = tmp_path / "New.Movie.2020.mkv"
    failed = tmp_path / "sub" / "Failed.Movie.2019.mp4"
    skipped = tmp_path / "Unknown.Thing.mkv"
    note = tmp_path / "readme.txt"
    failed.parent.mkdir()
    for f in (new, failed, skipped, note):
        f.write_text("x")

    log_watcher_event("scan", str(failed), "failed", "boom")
    log_watcher_event("scan", str(skipped), "skipped", "Movie metadata not found")

    m = WatcherManager()
    m.initial_scan(str(tmp_path))
    assert sorted(queued_paths(m)) == sorted([str(new), str(failed)])
    assert "4 files, 3 media, 2 queued" in m.last_scan_summary
    assert "1 skipped" in m.last_scan_summary


def test_scan_stops_retrying_after_max_failures(tmp_path):
    f = tmp_path / "Broken.2020.mkv"
    f.write_text("x")
    for _ in range(MAX_FAILED_ATTEMPTS):
        log_watcher_event("scan", str(f), "failed", "boom")
    m = WatcherManager()
    m.initial_scan(str(tmp_path))
    assert queued_paths(m) == []


def test_enqueue_dedupes_and_filters(tmp_path):
    m = WatcherManager()
    m.enqueue("created", "/in/a.mkv")
    m.enqueue("moved", "/in/a.mkv")
    m.enqueue("created", "/in/a.mkv.part")
    assert queued_paths(m) == ["/in/a.mkv"]
