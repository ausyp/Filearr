from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from backend.core.processor import process_file
from backend.core.config_service import config_service

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
