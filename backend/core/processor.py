from backend.core.cam_detector import is_cam
from backend.core.language import detect_language
from backend.core.quality import get_quality_score
from backend.core.decision import decide
from backend.core.file_ops import move_file, rejection_move
from backend.core.tmdb import get_movie_metadata
from backend.core.safety import evaluate_safety, extract_filename_language
from loguru import logger
import os

def process_file(path):
    filename = os.path.basename(path)
    logger.info(f"Processing file: {filename}")

    # 1. Check if CAM/TS
    if is_cam(filename):
        rejection_move(path, "CAM/TS detected")
        return {"status": "rejected", "reason": "CAM/TS detected"}

    # 2. Mandatory safety checks before parsing / TMDB lookup
    allowed, reason, pre_guess = evaluate_safety(path)
    if not allowed:
        logger.warning(f"Skipping {filename}: {reason}")
        return {"status": "skipped", "reason": reason}

    # 3. Get Metadata
    metadata = get_movie_metadata(filename, pre_guess=pre_guess)
    if not metadata or not metadata.get('tmdb_id'):
        logger.warning(f"Could not confidently identify movie for {filename}")
        return {"status": "skipped", "reason": "Low TMDB confidence"}

    # 4. Detect Language & Quality
    from backend.core.language import get_refined_language
    filename_lang = extract_filename_language(filename)
    language = get_refined_language(path, metadata, filename_lang=filename_lang)
    quality = get_quality_score(path)

    logger.info(f"Analyzed {filename}: Movie={metadata['title']} ({metadata['year']}), Lang={language}, Quality={quality}")

    # 5. Make Decision
    decision = decide(path, language, quality, False, metadata)

    # 6. Execute Decision
    if decision.action == "move":
        if os.path.exists(decision.destination):
            logger.warning(f"Skipping {filename}: destination exists ({decision.destination})")
            return {"status": "skipped", "reason": "Destination already exists"}
        move_file(path, decision.destination)
        return {"status": "processed", "reason": f"Moved to {os.path.basename(os.path.dirname(decision.destination))}"}
    elif decision.action == "reject":
        rejection_move(path, decision.reason)
        return {"status": "rejected", "reason": decision.reason}
    else:
        logger.info(f"Decision for {filename}: {decision.action} - {decision.reason}")
        return {"status": "ignored", "reason": decision.reason}
