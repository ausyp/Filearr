import subprocess
import json
import logging

logger = logging.getLogger(__name__)

def detect_language(path):
    """
    Detects the primary audio language of the file using ffprobe.
    Returns ISO 639-2 language code (e.g., 'mal', 'eng', 'hin', 'tam') or 'und' if undetermined.
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
        
        streams = data.get('streams', [])
        if not streams:
            return 'und'
            
        # Check first audio stream
        tags = streams[0].get('tags', {})
        lang = tags.get('language', '').lower()
        
        if not lang:
            return 'und'
            
        # Normalize common variations
        if lang in ['mal', 'malam', 'malayalam']:
            return 'mal'
        if lang in ['eng', 'english']:
            return 'eng'
        if lang in ['hin', 'hindi']:
            return 'hin'
        if lang in ['tam', 'tamil']:
            return 'tam'
            
        return lang
    except Exception as e:
        logger.error(f"Language detection failed for {path}: {e}")
        return 'und'
