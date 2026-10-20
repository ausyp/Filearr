from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from backend.core.processor import process_file, is_media_file
from backend.core.config_service import config_service
from backend.core.ignore_service import ignore_service
from backend.db.database import SessionLocal
from backend.db.models import WatcherLog
from datetime import datetime
import os
import queue
import time
import threading
from loguru import logger

SCAN_INTERVAL_SECONDS = 300  # 5 minutes
STABLE_CHECK_SECONDS = 2
STABLE_TIMEOUT_SECONDS = 6 * 60 * 60  # Give up waiting on a file still growing after 6h
RETRY_ACTIONS = ("failed", "detected")  # "detected" = interrupted mid-processing (e.g. restart)
MAX_FAILED_ATTEMPTS = 3

def log_watcher_event(event_type: str, file_path: str, action: str, reason: str = None):
    """Log watcher event to database"""
    db = SessionLocal()
    try:
        log_entry = WatcherLog(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            file_path=file_path,
            action=action,
            reason=reason
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log watcher event: {e}")
        db.rollback()
    finally:
        db.close()

def wait_until_stable(path: str, stop_event: threading.Event) -> bool:
    """
    Waits until the file size stops changing (download/copy finished).
    Returns False if the file disappeared, the wait timed out, or the watcher stopped.
    """
    deadline = time.monotonic() + STABLE_TIMEOUT_SECONDS
    last_size = -1
    while time.monotonic() < deadline:
        try:
            size = os.path.getsize(path)
        except OSError:
            return False
        if size == last_size and size > 0:
            return True
        last_size = size
        if stop_event.wait(STABLE_CHECK_SECONDS):
            return False
    logger.warning(f"Timed out waiting for {path} to finish writing")
    return False

class Handler(FileSystemEventHandler):
    def __init__(self, manager):
        self.manager = manager

    def on_created(self, event):
        if not event.is_directory:
            logger.info(f"Watcher Event: {event.event_type} - {event.src_path}")
            self.manager.enqueue("created", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            logger.info(f"File moved detected: {event.dest_path}")
            self.manager.enqueue("moved", event.dest_path)

class WatcherManager:
    def __init__(self):
        self.observer = None
        self.watched_path = None
        self.is_running = False
        self.stop_event = threading.Event()
        self.queue = queue.Queue()
        self.pending = set()
        self.pending_lock = threading.Lock()
        self.last_scan_summary = None

    def enqueue(self, event_type: str, file_path: str):
        """Queue a file for processing; duplicate events for a queued file are dropped"""
        if not is_media_file(file_path):
            return
        with self.pending_lock:
            if file_path in self.pending:
                return
            self.pending.add(file_path)
        self.queue.put((event_type, file_path))

    def start(self):
        if self.is_running:
            logger.info("Watcher is already running.")
            return

        input_dir = config_service.get_setting("INPUT_DIR")

        if not input_dir or not os.path.exists(input_dir):
            logger.warning(f"Input directory {input_dir} does not exist or not set. Watcher not started.")
            return

        # inotify events don't fire on network shares (SMB/NFS); polling works everywhere
        use_polling = str(config_service.get_setting("WATCHER_POLLING", "false")).lower() in ("1", "true", "yes")
        self.observer = PollingObserver(timeout=30) if use_polling else Observer()
        self.watched_path = input_dir
        # Fresh event per run so threads from a previous run exit instead of lingering
        self.stop_event = threading.Event()
        self.queue = queue.Queue()
        with self.pending_lock:
            self.pending.clear()

        logger.info(f"Starting watcher on {input_dir} ({'polling' if use_polling else 'native events'})")
        try:
            self.observer.schedule(Handler(self), input_dir, recursive=True)
            self.observer.start()
            self.is_running = True

            # Single worker processes files one at a time, so the observer,
            # periodic scan and manual events never race on the same file
            threading.Thread(
                target=self.worker_loop,
                args=(self.stop_event, self.queue),
                daemon=True,
                name="WatcherWorker"
            ).start()

            # Start background scan loop (Initial + Periodic)
            threading.Thread(
                target=self.background_scan_loop,
                args=(input_dir, self.stop_event),
                daemon=True,
                name="WatcherBackgroundScan"
            ).start()
            logger.info("Background scan loop started (Periodic: 5m)")

        except Exception as e:
            logger.error(f"Failed to start watcher on {input_dir}: {e}")

    def stop(self):
        self.stop_event.set()
        if self.observer:
            logger.info(f"Stopping watcher on {self.watched_path}")
            self.observer.stop()
            self.observer.join()
            self.observer = None
        self.is_running = False

    def restart(self):
        logger.info("Restarting watcher...")
        self.stop()
        self.start()

    def get_status(self):
        return {
            "is_running": self.is_running,
            "watched_path": self.watched_path
        }

    def worker_loop(self, stop_event: threading.Event, work_queue: queue.Queue):
        while not stop_event.is_set():
            try:
                event_type, file_path = work_queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                self.handle_file(event_type, file_path, stop_event)
            finally:
                with self.pending_lock:
                    self.pending.discard(file_path)

    def handle_file(self, event_type: str, file_path: str, stop_event: threading.Event):
        log_watcher_event(event_type, file_path, "detected")

        should_ignore, ignore_reason = ignore_service.should_ignore(file_path)
        if should_ignore:
            logger.info(f"Ignoring: {file_path} ({ignore_reason})")
            log_watcher_event(event_type, file_path, "ignored", ignore_reason)
            return

        if not wait_until_stable(file_path, stop_event):
            logger.info(f"Skipping {file_path}: file vanished or never finished writing")
            return

        try:
            result = process_file(file_path)
            status = result.get("status", "processed") if result else "processed"
            reason = result.get("reason") if result else None
            log_watcher_event(event_type, file_path, status, reason)
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            log_watcher_event(event_type, file_path, "failed", str(e))

    def background_scan_loop(self, directory: str, stop_event: threading.Event):
        """Background thread loop for initial and periodic scanning"""
        # 1. Initial Scan immediately, then 2. Periodic Scan every 5 minutes
        while not stop_event.is_set():
            self.initial_scan(directory)
            if stop_event.wait(SCAN_INTERVAL_SECONDS):
                break

    def initial_scan(self, directory: str):
        """
        Scan directory for files that still need processing. A file is queued if it
        has never been seen, or if its last attempt failed or was interrupted
        (up to MAX_FAILED_ATTEMPTS). Files whose last outcome was skipped/ignored
        are left alone, and the summary line says so.
        """
        total = media = queued = 0
        left_alone = {}  # last action -> count
        
        db = SessionLocal()
        try:
            if not os.path.isdir(directory):
                logger.warning(f"Scan skipped: {directory} is missing or not a directory (is the volume mounted?)")
                return

            for root, dirs, files in os.walk(directory):
                for file in files:
                    total += 1
                    if not is_media_file(file):
                        continue
                    media += 1
                        
                    file_path = os.path.join(root, file)
                    
                    last = (
                        db.query(WatcherLog.action)
                        .filter(WatcherLog.file_path == file_path)
                        .order_by(WatcherLog.id.desc())
                        .first()
                    )
                    retry = False
                    if last is not None and last.action in RETRY_ACTIONS:
                        failures = (
                            db.query(WatcherLog.id)
                            .filter(WatcherLog.file_path == file_path, WatcherLog.action == "failed")
                            .count()
                        )
                        retry = failures < MAX_FAILED_ATTEMPTS
                    if last is None or retry:
                        logger.info(f"Scan queued {'new' if last is None else 'retry of'} file: {file_path}")
                        self.enqueue("scan", file_path)
                        queued += 1
                    else:
                        left_alone[last.action] = left_alone.get(last.action, 0) + 1

            breakdown = ", ".join(f"{n} {action}" for action, n in sorted(left_alone.items())) or "none"
            summary = (
                f"Scan of {directory}: {total} files, {media} media, {queued} queued; "
                f"left alone from earlier runs: {breakdown}"
            )
            # Only repeat an unchanged summary at debug level so idle scans don't flood the log
            if queued or summary != self.last_scan_summary:
                logger.info(summary)
            else:
                logger.debug(summary)
            self.last_scan_summary = summary
        except Exception as e:
            logger.error(f"Scan failed: {e}")
        finally:
            db.close()

watcher_manager = WatcherManager()

def start_watchers():
    """Legacy helper for app startup"""
    watcher_manager.start()
