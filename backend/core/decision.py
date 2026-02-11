from pydantic import BaseModel
import os
from backend.core.config_service import config_service

class Decision(BaseModel):
    action: str  # 'move', 'replace', 'reject', 'ignore'
    destination: str
    reason: str

def decide(file_path, language, quality_score, is_cam, tmdb_info, existing_file=None):
    config = config_service.get_all_settings()
    
    if is_cam:
        rejected_dir = config.get("REJECTED_DIR", "/media/movies/.rejected")
        return Decision(
            action="reject",
            destination=os.path.join(rejected_dir, os.path.basename(file_path)),
            reason="CAM/TS file detected"
        )
    
    # Dynamic routing based on language
    destination_root = config.get("MOVIES_DIR", "/media/movies")
    
    if language == "mal":
        destination_root = config.get("MALAYALAM_DIR", "/media/movies/malayalam")
    
    # Construct final path: Destination/Title (Year)/Title (Year).ext
    title = tmdb_info.get('title', 'Unknown')
    year = tmdb_info.get('year', 'Unknown')
    ext = file_path.split('.')[-1]
    
    folder_name = f"{title} ({year})"
    file_name = f"{title} ({year}).{ext}"
    
    final_path = os.path.join(destination_root, folder_name, file_name)
    
    return Decision(
        action="move",
        destination=final_path,
        reason=f"Processed (Language: {language})"
    )
