import os
from backend.core.processor import process_file
from backend.core.language import detect_language
from backend.config.settings import settings
from backend.db.database import SessionLocal
from backend.db.models import CleanupLog, ErrorLog
from datetime import datetime
from loguru import logger
import traceback

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

class CleanupManager:
    def __init__(self):
        self.is_running = False
        self.should_stop = False
        self.current_file = ""

    def start(self):
        self.is_running = True
        self.should_stop = False

    def stop(self):
        if self.is_running:
            self.should_stop = True

    def finish(self):
        self.is_running = False
        self.should_stop = False
        self.current_file = ""

cleanup_manager = CleanupManager()

def run_manual_cleanup(origin_dir: str, malayalam_dest: str, english_dest: str, dry_run: bool = True):
    """
    Scans origin_dir and processes files, routing them based on detected language.
    If dry_run is True, it simulates the actions.
    """
    from backend.core.tmdb import get_movie_metadata
    from backend.core.safety import evaluate_safety, extract_filename_language
    from backend.core.decision import decide
    from backend.core.quality import get_quality_score
    from backend.core.file_ops import move_file
    
    cleanup_manager.start()
    logger.info(f"Starting manual cleanup: Origin={origin_dir}, Malayalam={malayalam_dest}, English={english_dest}, DryRun={dry_run}")
    
    log_cleanup("scan", origin_dir, None, "success", f"Started cleanup (dry_run={dry_run})")
    
    try:
        if not os.path.exists(origin_dir):
            error_msg = f"Origin directory {origin_dir} does not exist."
            logger.error(error_msg)
            log_error("cleanup", error_msg, "ERROR")
            raise FileNotFoundError(error_msg)

        processed_count = 0
        moved_count = 0
        failed_count = 0
        
        for root, dirs, files in os.walk(origin_dir):
            if cleanup_manager.should_stop:
                logger.info("Cleanup operation cancelled by user.")
                break

            logger.info(f"Scanning directory: {root} (Found {len(files)} files)")
            if not files:
                continue
                
            for file in files:
                if cleanup_manager.should_stop:
                    break

                file_path = os.path.join(root, file)
                cleanup_manager.current_file = file
                
                # Skip non-media files
                if not file.lower().endswith(('.mkv', '.mp4', '.avi', '.mov')):
                    continue

                logger.info(f"Checking file: {file}")
                try:
                    # 1. Mandatory safety checks before parsing / TMDB lookup
                    allowed, reason, pre_guess = evaluate_safety(file_path)
                    if not allowed:
                        logger.warning(f"Skipping {file}: {reason}")
                        log_cleanup("skip", file_path, None, "success", reason)
                        continue

                    # 2. Get Metadata (Renaming starts here)
                    metadata = get_movie_metadata(file, pre_guess=pre_guess)
                    if not metadata or not metadata.get('tmdb_id'):
                        logger.warning(f"Could not confidently identify movie for {file}")
                        log_cleanup("skip", file_path, None, "success", "Low TMDB confidence")
                        continue

                    # 3. Detect Language & Quality
                    from backend.core.language import get_refined_language
                    filename_lang = extract_filename_language(file)
                    lang_code = get_refined_language(file_path, metadata, filename_lang=filename_lang)
                    quality = get_quality_score(file_path)

                    # 4. Make Decision (Using overrides for manual destinations)
                    decision = decide(
                        file_path=file_path,
                        language=lang_code,
                        quality_score=quality,
                        is_cam=False, # Manual cleanup assumes filtered files
                        tmdb_info=metadata,
                        movies_dir_override=english_dest,
                        mal_dir_override=malayalam_dest
                    )
                    
                    dest_path = decision.destination
                    
                    if os.path.exists(dest_path):
                        logger.warning(f"Skipping {file}: destination exists ({dest_path})")
                        log_cleanup("skip", file_path, dest_path, "success", "Destination already exists")
                        continue

                    if dry_run:
                        logger.info(f"[DRY RUN] Would move {file_path} to {dest_path} (Lang Code: {lang_code})")
                        log_cleanup("dry_run", file_path, dest_path, "success", f"Language Code: {lang_code}")
                    else:
                        # 5. Execute Move/Rename
                        # Shared move_file handles directory creation and logging
                        if move_file(file_path, dest_path):
                            log_cleanup("move", file_path, dest_path, "success", f"Language Code: {lang_code}")
                            moved_count += 1
                        else:
                            raise Exception(f"Move failed for {file_path}")
                    
                    processed_count += 1
                            
                except Exception as e:
                    error_msg = f"Error processing {file_path}: {str(e)}"
                    logger.error(error_msg)
                    log_error("cleanup", error_msg, "ERROR", traceback.format_exc())
                    log_cleanup("move", file_path, None, "failed", str(e))
                    failed_count += 1
                        
        status = "cancelled" if cleanup_manager.should_stop else "success"
        summary = f"Summary: Processed {processed_count} files, Moved {moved_count}, Failed {failed_count} ({status})"
        logger.info(summary)
        log_cleanup("scan", origin_dir, None, status, summary)
    finally:
        cleanup_manager.finish()
