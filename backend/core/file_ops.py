import shutil
import os
import logging
from backend.core.config_service import config_service

logger = logging.getLogger(__name__)

def unique_path(dest):
    """
    Returns dest, or "name (1).ext", "name (2).ext", ... if dest already exists.
    """
    if not os.path.exists(dest):
        return dest
    base, ext = os.path.splitext(dest)
    i = 1
    while os.path.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"

def move_file(src, dest):
    """
    Safely moves a file from src to dest, creating parent directories if needed.
    Never overwrites an existing file at dest.
    """
    try:
        if not os.path.exists(src):
            logger.error(f"Source file {src} does not exist.")
            return False

        if os.path.exists(dest):
            logger.error(f"Refusing to move {src}: destination {dest} already exists.")
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
    Moves a file to the rejected folder (Trash is unified with Rejections).
    """
    config = config_service.get_all_settings()
    rejected_dir = config.get("REJECTED_DIR", "/media/movies/rejected")
    
    filename = os.path.basename(src)
    dest = unique_path(os.path.join(rejected_dir, filename))
    logger.warning(f"Rejecting {filename}: {reason}")
    return move_file(src, dest)

def trash_move(src):
    """
    Moves a file to the rejected folder (Trash is unified with Rejections).
    """
    return rejection_move(src, "Trashed")
