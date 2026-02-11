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
        if not event.is_directory:
            logger.info(f"New file detected: {event.src_path}")
            log_watcher_event("created", event.src_path, "detected")
            
            # Check if file should be ignored
            should_ignore, ignore_reason = ignore_service.should_ignore(event.src_path)
            if should_ignore:
                logger.info(f"Ignoring file {event.src_path}: {ignore_reason}")
                log_watcher_event("created", event.src_path, "ignored", ignore_reason)
                return
            
            # Add a small delay to ensure file is fully written/moved
            time.sleep(2) 
            try:
                process_file(event.src_path)
                log_watcher_event("created", event.src_path, "processed")
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
                process_file(event.dest_path)
                log_watcher_event("moved", event.dest_path, "processed")
            except Exception as e:
                error_msg = f"Error processing moved file {event.dest_path}: {e}"
                logger.error(error_msg)
                log_watcher_event("moved", event.dest_path, "failed", str(e))

def start_watchers():
    input_dir = config_service.get_setting("INPUT_DIR")
    
    if not input_dir or not os.path.exists(input_dir):
        logger.warning(f"Input directory {input_dir} does not exist or not set. Watcher not started for input.")
        return

    observer = Observer()
    event_handler = Handler()
    
    logger.info(f"Starting watcher on {input_dir}")
    try:
        observer.schedule(event_handler, input_dir, recursive=True)
        observer.start()
    except Exception as e:
        logger.error(f"Failed to start watcher on {input_dir}: {e}")
    
    # The observer runs in a separate thread, so we don't need a while loop here 
    # if this function is called from a non-blocking context (like FastAPI startup event)
