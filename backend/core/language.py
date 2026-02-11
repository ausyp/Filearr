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
            
        # Check all audio streams
        for stream in streams:
            tags = stream.get('tags', {})
            lang = tags.get('language', '').lower()
            
            if not lang:
                continue
                
            # Normalize common variations
            if lang in ['mal', 'may', 'malam', 'malayalam']:
                return 'mal'
            if lang in ['eng', 'english']:
                return 'eng'
            if lang in ['hin', 'hindi']:
                return 'hin'
            if lang in ['tam', 'tamil']:
                return 'tam'
            
            # If we find a non-'und' language, keep it if we don't find others
            # But we prefer matching our known list first
            
        # If no known language found, return the first one that wasn't empty or 'und'
        for stream in streams:
            lang = stream.get('tags', {}).get('language', '').lower()
            if lang and lang != 'und':
                return lang
                
        return 'und'
    except Exception as e:
        logger.error(f"Language detection failed for {path}: {e}")
        return 'und'
