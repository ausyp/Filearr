from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from backend.core.processor import process_file
from backend.config.settings import settings
import time
from loguru import logger
import os

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            logger.info(f"New file detected: {event.src_path}")
            # Add a small delay to ensure file is fully written/moved
            time.sleep(2) 
            try:
                process_file(event.src_path)
            except Exception as e:
                logger.error(f"Error processing file {event.src_path}: {e}")

    def on_moved(self, event):
        if not event.is_directory:
            logger.info(f"File moved detected: {event.dest_path}")
            try:
                process_file(event.dest_path)
            except Exception as e:
                logger.error(f"Error processing moved file {event.dest_path}: {e}")

def start_watchers():
    if not os.path.exists(settings.INPUT_DIR):
        logger.warning(f"Input directory {settings.INPUT_DIR} does not exist. Watcher not started for input.")
        return

    observer = Observer()
    event_handler = Handler()
    
    logger.info(f"Starting watcher on {settings.INPUT_DIR}")
    observer.schedule(event_handler, settings.INPUT_DIR, recursive=True)
    
    # You might want to watch other directories too based on config
    # if settings.WATCH_MOVIES:
    #     observer.schedule(event_handler, f"{settings.OUTPUT_DIR}/movies", recursive=True)
    
    observer.start()
    
    # The observer runs in a separate thread, so we don't need a while loop here 
    # if this function is called from a non-blocking context (like FastAPI startup event)
