import shutil
import os
import logging
from backend.core.config_service import config_service

logger = logging.getLogger(__name__)

def apply_permissions(path):
    """
    Applies PUID and PGID to the given path if running on Linux.
    """
    if os.name == 'nt':
        return # chown not supported on Windows
        
    puid = os.getenv("PUID")
    pgid = os.getenv("PGID")
    
    if puid and pgid:
        try:
            uid = int(puid)
            gid = int(pgid)
            os.chown(path, uid, gid)
            # Also set permissions to 775 for directories or 664 for files
            if os.path.isdir(path):
                os.chmod(path, 0o775)
            else:
                os.chmod(path, 0o664)
        except Exception as e:
            logger.error(f"Failed to apply permissions to {path}: {e}")

def move_file(src, dest):
    """
    Safely moves a file from src to dest, creating parent directories if needed.
    """
    try:
        if not os.path.exists(src):
            logger.error(f"Source file {src} does not exist.")
            return False
            
        dest_dir = os.path.dirname(dest)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
            apply_permissions(dest_dir)
        
        shutil.move(src, dest)
        apply_permissions(dest)
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
