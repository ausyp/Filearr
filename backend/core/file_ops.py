import shutil
import os
import logging
from backend.core.config_service import config_service

logger = logging.getLogger(__name__)

def move_file(src, dest):
    """
    Safely moves a file from src to dest, creating parent directories if needed.
    """
    try:
        if not os.path.exists(src):
            logger.error(f"Source file {src} does not exist.")
            return False
            
        dest_dir = os.path.dirname(dest)
        os.makedirs(dest_dir, exist_ok=True)
        
        shutil.move(src, dest)
        logger.info(f"Moved {src} -> {dest}")
        return True
    except Exception as e:
        logger.error(f"Failed to move {src} to {dest}: {e}")
        return False

def rejection_move(src, reason):
    """
    Moves a file to the rejected folder.
    """
    config = config_service.get_all_settings()
    rejected_dir = config.get("REJECTED_DIR", "/media/movies/rejected")
    
    filename = os.path.basename(src)
    dest = os.path.join(rejected_dir, filename)
    logger.warning(f"Rejecting {filename}: {reason}")
    return move_file(src, dest)

def trash_move(src):
    """
    Moves a file to the rejected folder (Trash is unified with Rejections).
    """
    config = config_service.get_all_settings()
    rejected_dir = config.get("REJECTED_DIR", "/media/movies/rejected")
    
    filename = os.path.basename(src)
    dest = os.path.join(rejected_dir, filename)
    logger.info(f"Trashing {filename} (Moving to rejected folder)")
    return move_file(src, dest)
