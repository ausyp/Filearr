import os
from backend.core.processor import process_file
from backend.core.language import detect_language
from backend.config.settings import settings
from backend.db.database import SessionLocal
from backend.db.models import CleanupLog, ErrorLog
from datetime import datetime
import logging
import traceback

logger = logging.getLogger(__name__)

def log_cleanup(operation_type: str, file_path: str, destination: str = None, status: str = "success", details: str = None):
    """Log cleanup operation to database"""
    db = SessionLocal()
    try:
        log_entry = CleanupLog(
            timestamp=datetime.utcnow(),
            operation_type=operation_type,
            file_path=file_path,
            destination=destination,
            status=status,
            details=details
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log cleanup operation: {e}")
        db.rollback()
    finally:
        db.close()

def log_error(source: str, message: str, level: str = "ERROR", tb: str = None):
    """Log error to database"""
    db = SessionLocal()
    try:
        error_entry = ErrorLog(
            timestamp=datetime.utcnow(),
            level=level,
            source=source,
            message=message,
            traceback=tb
        )
        db.add(error_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log error: {e}")
        db.rollback()
    finally:
        db.close()

def run_manual_cleanup(origin_dir: str, malayalam_dest: str, english_dest: str, dry_run: bool = True):
    """
    Scans origin_dir and processes files, routing them based on detected language.
    If dry_run is True, it simulates the actions.
    """
    logger.info(f"Starting manual cleanup: Origin={origin_dir}, Malayalam={malayalam_dest}, English={english_dest}, DryRun={dry_run}")
    
    log_cleanup("scan", origin_dir, None, "success", f"Started cleanup (dry_run={dry_run})")
    
    if not os.path.exists(origin_dir):
        error_msg = f"Origin directory {origin_dir} does not exist."
        logger.error(error_msg)
        log_error("cleanup", error_msg, "ERROR")
        raise FileNotFoundError(error_msg)

    processed_count = 0
    moved_count = 0
    failed_count = 0
    
    for root, dirs, files in os.walk(origin_dir):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip small files or non-media files if needed
            if file.lower().endswith(('.mkv', '.mp4', '.avi', '.mov')):
                logger.info(f"Scanning file: {file_path}")
                processed_count += 1
                
                try:
                    # Detect language code
                    lang_code = detect_language(file_path)
                    
                    # Determine destination based on language
                    if lang_code == "mal":
                        dest_dir = malayalam_dest
                    else:
                        dest_dir = english_dest
                    
                    dest_path = os.path.join(dest_dir, file)
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would move {file_path} to {dest_path} (Lang Code: {lang_code})")
                        log_cleanup("dry_run", file_path, dest_path, "success", f"Language Code: {lang_code}")
                    else:
                        # Ensure destination directory exists
                        os.makedirs(dest_dir, exist_ok=True)
                        
                        # Move file
                        import shutil
                        shutil.move(file_path, dest_path)
                        logger.info(f"Moved {file_path} to {dest_path}")
                        log_cleanup("move", file_path, dest_path, "success", f"Language Code: {lang_code}")
                        moved_count += 1
                        
                except Exception as e:
                    error_msg = f"Error processing {file_path}: {str(e)}"
                    logger.error(error_msg)
                    log_error("cleanup", error_msg, "ERROR", traceback.format_exc())
                    log_cleanup("move", file_path, None, "failed", str(e))
                    failed_count += 1
                    
    summary = f"Cleanup complete. Processed {processed_count} files, Moved {moved_count}, Failed {failed_count}"
    logger.info(summary)
    log_cleanup("scan", origin_dir, None, "success", summary)
