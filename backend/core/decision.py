from pydantic import BaseModel
import os
from backend.core.config_service import config_service

class Decision(BaseModel):
    action: str  # 'move', 'replace', 'reject', 'ignore'
    destination: str
    reason: str

import re

def sanitize_filename(filename):
    """Sanitize filename to be safe for all filesystems."""
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()



def extract_quality_tags(file_path: str) -> str:
    """Extract common release quality tags (e.g., 1080p, BluRay) from source filename."""
    stem = os.path.splitext(os.path.basename(file_path))[0]
    tag_patterns = [
        r"2160p", r"1080p", r"720p", r"480p",
        r"bluray", r"blu[- ]?ray", r"brrip", r"bdrip", r"web[- .]?dl", r"webrip", r"hdrip", r"dvdrip",
        r"x264", r"x265", r"h\.264", r"h\.265", r"hevc", r"av1",
        r"dts", r"ddp?5\.1", r"aac", r"atmos", r"truehd",
    ]

    found = []
    for pat in tag_patterns:
        m = re.search(rf"(?i)(?<![a-z0-9])({pat})(?![a-z0-9])", stem)
        if m:
            normalized = m.group(1).replace(' ', '.').replace('-', '.').upper()
            found.append(normalized)

    tags = []
    for tag in found:
        if tag not in tags:
            tags.append(tag)

    return " ".join(tags)


def decide(file_path, language, quality_score, is_cam, tmdb_info, existing_file=None, movies_dir_override=None, mal_dir_override=None):
    config = config_service.get_all_settings()
    
    if is_cam:
        rejected_dir = config.get("REJECTED_DIR", "/media/movies/.rejected")
        return Decision(
            action="reject",
            destination=os.path.join(rejected_dir, os.path.basename(file_path)),
            reason="CAM/TS file detected"
        )
    
    # Dynamic routing based on language
    destination_root = movies_dir_override or config.get("MOVIES_DIR", "/media/movies")
    
    if language == "mal":
        destination_root = mal_dir_override or config.get("MALAYALAM_DIR", "/media/movies/malayalam")
    
    # Construct final path: Destination/Title (Year)/Title (Year).ext
    title = sanitize_filename(tmdb_info.get('title', 'Unknown'))
    year = tmdb_info.get('year', 'Unknown')
    ext = file_path.split('.')[-1]
    
    # Format: Movie Title (Year) or just Movie Title if year is missing
    folder_name = f"{title} ({year})" if year and year != "Unknown" else title

    # Preserve important release quality markers in final filename.
    quality_tags = extract_quality_tags(file_path)
    file_stem = f"{folder_name} {quality_tags}".strip()
    file_name = f"{file_stem}.{ext}"
    
    # Final path ensures movie is in its own subfolder
    final_path = os.path.join(destination_root, folder_name, file_name)
    
    return Decision(
        action="move",
        destination=final_path,
        reason=f"Processed (Language: {language})"
    )
