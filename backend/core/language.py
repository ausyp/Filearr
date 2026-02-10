import subprocess
import json
import logging

logger = logging.getLogger(__name__)

def detect_language(path):
    """
    Detects the primary audio language of the file using ffprobe.
    Returns 'mal' for Malayalam, otherwise 'other'.
    """
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream_tags=language",
            "-of", "json",
            path
        ]
        # In a real deployed environment, ensure ffprobe is in PATH
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
        data = json.loads(output)
        
        for stream in data.get('streams', []):
            tags = stream.get('tags', {})
            lang = tags.get('language', '').lower()
            if lang == 'mal' or lang == 'malayalam':
                return 'mal'
                
        return 'other'
    except Exception as e:
        logger.error(f"Language detection failed for {path}: {e}")
        return 'other'
