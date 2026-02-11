from backend.core.cam_detector import is_cam
from backend.core.language import detect_language
from backend.core.quality import get_quality_score
from backend.core.decision import decide
from backend.core.file_ops import move_file, rejection_move
from backend.core.tmdb import get_movie_metadata
from loguru import logger
import os

def process_file(path):
    filename = os.path.basename(path)
    logger.info(f"Processing file: {filename}")

    # 1. Check if CAM/TS
    if is_cam(filename):
        rejection_move(path, "CAM/TS detected")
        return {"status": "rejected", "reason": "CAM/TS detected"}

    # 2. Get Metadata
    metadata = get_movie_metadata(filename)
    if not metadata:
        logger.warning(f"Could not identify movie for {filename}")
        # Optionally move to manual review folder or skip
        return {"status": "skipped", "reason": "Movie metadata not found"}

    # 3. Detect Language & Quality
    from backend.core.language import get_refined_language
    language = get_refined_language(path, metadata)
    quality = get_quality_score(path)

    logger.info(f"Analyzed {filename}: Movie={metadata['title']} ({metadata['year']}), Lang={language}, Quality={quality}")

    # 4. Make Decision
    decision = decide(path, language, quality, False, metadata)

    # 5. Execute Decision
    if decision.action == "move":
        move_file(path, decision.destination)
        return {"status": "processed", "reason": f"Moved to {os.path.basename(os.path.dirname(decision.destination))}"}
    elif decision.action == "reject":
        rejection_move(path, decision.reason)
        return {"status": "rejected", "reason": decision.reason}
    else:
        logger.info(f"Decision for {filename}: {decision.action} - {decision.reason}")
        return {"status": "ignored", "reason": decision.reason}
