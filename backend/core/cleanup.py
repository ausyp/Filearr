import os
from backend.core.processor import process_file
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)

def run_manual_cleanup(origin_dir: str, dest_dir: str, dry_run: bool = True):
    """
    Scans origin_dir and processes files.
    If dry_run is True, it simulates the actions.
    """
    logger.info(f"Starting manual cleanup: Origin={origin_dir}, Dest={dest_dir}, DryRun={dry_run}")
    
    if not os.path.exists(origin_dir):
        logger.error(f"Origin directory {origin_dir} does not exist.")
        return

    count = 0
    for root, dirs, files in os.walk(origin_dir):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip small files or non-media files if needed
            if file.lower().endswith(('.mkv', '.mp4', '.avi', '.mov')):
                logger.info(f"Scanning file: {file_path}")
                try:
                    # In a real implementation, process_file would need a dry_run flag
                    # or return a plan object. For now, we logging.
                    if dry_run:
                        logger.info(f"[DRY RUN] Would process {file_path}")
                    else:
                        process_file(file_path)
                    count += 1
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    
    logger.info(f"Cleanup complete. Processed {count} files.")
