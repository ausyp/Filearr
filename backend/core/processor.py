from backend.core.cam_detector import is_cam
from backend.core.language import get_refined_language
from backend.core.quality import get_quality_score
from backend.core.decision import decide
from backend.core.file_ops import move_file, rejection_move
from backend.core.tmdb import get_movie_metadata
from backend.core.safety import evaluate_safety, extract_filename_language
from backend.core.tv import parse_episode, get_show_metadata, decide_episode, episode_label, MIN_EPISODE_SIZE_BYTES
from backend.db.database import SessionLocal
from backend.db.models import ProcessedFile, RejectedFile
from loguru import logger
import os

MEDIA_EXTENSIONS = ('.mkv', '.mp4', '.avi', '.mov', '.m4v', '.ts')

def is_media_file(path):
    return path.lower().endswith(MEDIA_EXTENSIONS)

def log_processed_file(path, destination, metadata, language, quality, action="move"):
    """Record a processed file for the dashboard"""
    db = SessionLocal()
    try:
        db.add(ProcessedFile(
            filename=os.path.basename(path),
            original_path=path,
            destination_path=destination,
            movie_name=metadata.get('title', 'Unknown'),
            year=str(metadata.get('year') or 'Unknown'),
            language=language,
            quality_score=quality,
            action=action,
        ))
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log processed file {path}: {e}")
        db.rollback()
    finally:
        db.close()

def record_rejected(path, reason):
    """Record a rejected file for the dashboard"""
    db = SessionLocal()
    try:
        db.add(RejectedFile(filename=os.path.basename(path), reason=reason))
        db.commit()
    except Exception as e:
        logger.error(f"Failed to record rejected file {path}: {e}")
        db.rollback()
    finally:
        db.close()

def reject(path, reason):
    if not rejection_move(path, reason):
        return {"status": "failed", "reason": f"Could not move to rejected folder ({reason})"}
    record_rejected(path, reason)
    return {"status": "rejected", "reason": reason}

def execute_move(path, decision, metadata, language, quality):
    filename = os.path.basename(path)
    if os.path.exists(decision.destination):
        logger.warning(f"Skipping {filename}: destination exists ({decision.destination})")
        return {"status": "skipped", "reason": "Destination already exists"}
    if not move_file(path, decision.destination):
        return {"status": "failed", "reason": f"Move to {decision.destination} failed"}
    log_processed_file(path, decision.destination, metadata, language, quality, action="move")
    return {"status": "processed", "reason": f"Moved to {os.path.basename(os.path.dirname(decision.destination))}"}

def process_episode(path, guess):
    """TV episodes skip the movie safety checks (no year, smaller files) and go to the TV folders"""
    filename = os.path.basename(path)
    if "sample" in filename.lower():
        return {"status": "skipped", "reason": "Sample file"}
    try:
        if os.path.getsize(path) < MIN_EPISODE_SIZE_BYTES:
            return {"status": "skipped", "reason": "Too small to be a full episode"}
    except OSError:
        return {"status": "skipped", "reason": "Unable to determine file size"}

    show = get_show_metadata(guess)
    if not show:
        logger.warning(f"Could not confidently identify TV show for {filename}")
        return {"status": "skipped", "reason": "Low TMDB confidence (TV)"}

    filename_lang = extract_filename_language(filename)
    language = get_refined_language(path, show, filename_lang=filename_lang)
    quality = get_quality_score(path)

    decision = decide_episode(path, language, guess, show)
    logger.info(f"Analyzed {filename}: Show={show['title']} ({show['year']}), Lang={language}, Quality={quality}")

    # Dashboard shows "Show S01E05" in the title column
    metadata = {"title": f"{show['title']} {episode_label(guess)}", "year": show["year"]}
    return execute_move(path, decision, metadata, language, quality)

def process_file(path):
    filename = os.path.basename(path)
    logger.info(f"Processing file: {filename}")

    if not os.path.isfile(path):
        return {"status": "skipped", "reason": "File no longer exists"}

    # 1. Check if CAM/TS
    if is_cam(filename):
        return reject(path, "CAM/TS detected")

    # 2. TV episodes have their own checks and folders
    episode = parse_episode(filename)
    if episode:
        return process_episode(path, episode)

    # 3. Mandatory safety checks before parsing / TMDB lookup
    allowed, reason, pre_guess = evaluate_safety(path)
    if not allowed:
        logger.warning(f"Skipping {filename}: {reason}")
        return {"status": "skipped", "reason": reason}

    # 4. Get Metadata
    metadata = get_movie_metadata(filename, pre_guess=pre_guess)
    if not metadata or not metadata.get('tmdb_id'):
        logger.warning(f"Could not confidently identify movie for {filename}")
        return {"status": "skipped", "reason": "Low TMDB confidence"}

    # 5. Detect Language & Quality
    filename_lang = extract_filename_language(filename)
    language = get_refined_language(path, metadata, filename_lang=filename_lang)
    quality = get_quality_score(path)

    logger.info(f"Analyzed {filename}: Movie={metadata['title']} ({metadata['year']}), Lang={language}, Quality={quality}")

    # 6. Make Decision
    decision = decide(path, language, quality, False, metadata)

    # 7. Execute Decision
    if decision.action == "move":
        return execute_move(path, decision, metadata, language, quality)
    elif decision.action == "reject":
        return reject(path, decision.reason)
    else:
        logger.info(f"Decision for {filename}: {decision.action} - {decision.reason}")
        return {"status": "ignored", "reason": decision.reason}
