from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from backend.core.processor import process_file
from backend.core.config_service import config_service
from backend.core.ignore_service import ignore_service
from backend.db.database import SessionLocal
from backend.db.models import WatcherLog
from datetime import datetime
import os
import time
import threading
from loguru import logger

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

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        logger.info(f"Watcher Event: {event.event_type} - {event.src_path}")
        if not event.is_directory:
            log_watcher_event("created", event.src_path, "detected")
            
            # Check if file should be ignored
            should_ignore, ignore_reason = ignore_service.should_ignore(event.src_path)
            if should_ignore:
                logger.info(f"Ignoring: {event.src_path} ({ignore_reason})")
                log_watcher_event("created", event.src_path, "ignored", ignore_reason)
                return
            
            # Add a small delay to ensure file is fully written/moved
            logger.info(f"File is valid. Waiting 2s for handle to clear: {event.src_path}")
            time.sleep(2) 
            try:
                result = process_file(event.src_path)
                status = result.get("status", "processed") if result else "processed"
                reason = result.get("reason") if result else None
                log_watcher_event("created", event.src_path, status, reason)
            except Exception as e:
                error_msg = f"Error processing file {event.src_path}: {e}"
                logger.error(error_msg)
                log_watcher_event("created", event.src_path, "failed", str(e))

    def on_moved(self, event):
        if not event.is_directory:
            logger.info(f"File moved detected: {event.dest_path}")
            log_watcher_event("moved", event.dest_path, "detected")
            
            # Check if file should be ignored
            should_ignore, ignore_reason = ignore_service.should_ignore(event.dest_path)
            if should_ignore:
                logger.info(f"Ignoring moved file {event.dest_path}: {ignore_reason}")
                log_watcher_event("moved", event.dest_path, "ignored", ignore_reason)
                return
            
            try:
                result = process_file(event.dest_path)
                status = result.get("status", "processed") if result else "processed"
                reason = result.get("reason") if result else None
                log_watcher_event("moved", event.dest_path, status, reason)
            except Exception as e:
                error_msg = f"Error processing moved file {event.dest_path}: {e}"
                logger.error(error_msg)
                log_watcher_event("moved", event.dest_path, "failed", str(e))

class WatcherManager:
    def __init__(self):
        self.observer = None
        self.watched_path = None
        self.is_running = False

    def start(self):
        if self.is_running:
            logger.info("Watcher is already running.")
            return

        input_dir = config_service.get_setting("INPUT_DIR")
        
        if not input_dir or not os.path.exists(input_dir):
            logger.warning(f"Input directory {input_dir} does not exist or not set. Watcher not started.")
            return

        self.observer = Observer()
        self.event_handler = Handler()
        self.watched_path = input_dir
        
        logger.info(f"Starting watcher on {input_dir}")
        try:
            # Diagnostic: List contents of watch folder
            if os.path.isdir(input_dir):
                contents = os.listdir(input_dir)
                logger.info(f"Initial contents of {input_dir}: {contents}")
            
            self.observer.schedule(self.event_handler, input_dir, recursive=True)
            self.observer.start()
            self.is_running = True
            
            # Start background scan loop (Initial + Periodic)
            scan_thread = threading.Thread(
                target=self.background_scan_loop,
                args=(input_dir,),
                daemon=True,
                name="WatcherBackgroundScan"
            )
            scan_thread.start()
            logger.info("Background scan loop started (Periodic: 5m)")
            
        except Exception as e:
            logger.error(f"Failed to start watcher on {input_dir}: {e}")

    def stop(self):
        if self.observer:
            logger.info(f"Stopping watcher on {self.watched_path}")
            self.observer.stop()
            self.observer.join()
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

    def background_scan_loop(self, directory: str):
        """Background thread loop for initial and periodic scanning"""
        # 1. Initial Scan immediately
        self.initial_scan(directory)
        
        # 2. Periodic Scan every 5 minutes
        while self.is_running:
            time.sleep(300) # 5 minutes
            if self.is_running:
                logger.info(f"Triggering periodic 5-minute scan of {directory}...")
                self.initial_scan(directory)

    def initial_scan(self, directory: str):
        """Scan directory for existing files that haven't been processed"""
        logger.info(f"Starting initial scan of {directory}...")
        count = 0
        
        db = SessionLocal()
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    # Filter for known media extensions
                    if not file.lower().endswith(('.mkv', '.mp4', '.avi', '.m4v', '.ts')):
                        continue
                        
                    file_path = os.path.join(root, file)
                    
                    # Check if already processed (exists in WatcherLog)
                    exists = db.query(WatcherLog).filter(WatcherLog.file_path == file_path).first()
                    if not exists:
                        logger.info(f"Initial scan found new file: {file_path}")
                        try:
                            # Log as detected
                            log_watcher_event("scan", file_path, "detected")
                            
                            # Process it
                            result = process_file(file_path)
                            status = result.get("status", "processed") if result else "processed"
                            reason = result.get("reason") if result else None
                            
                            # Log result
                            log_watcher_event("scan", file_path, status, reason)
                            count += 1
                        except Exception as e:
                            logger.error(f"Failed to process {file_path} during initial scan: {e}")
                            log_watcher_event("scan", file_path, "failed", str(e))
                            
            logger.info(f"Initial scan complete. Processed {count} new files.")
        except Exception as e:
            logger.error(f"Initial scan failed: {e}")
        finally:
            db.close()

watcher_manager = WatcherManager()

def start_watchers():
    """Legacy helper for app startup"""
    watcher_manager.start()
