from pydantic import BaseModel

class Decision(BaseModel):
    action: str  # 'move', 'replace', 'reject', 'ignore'
    destination: str
    reason: str

def decide(file_path, language, quality_score, is_cam, tmdb_info, existing_file=None):
    if is_cam:
        return Decision(
            action="reject",
            destination="/output/.rejected",
            reason="CAM/TS file detected"
        )
    
    destination_root = "/output/movies"
    if language == "mal":
        destination_root = "/output/malayalam-movies"
        
    # Construct final path: /output/movies/Title (Year)/Title (Year).ext
    title = tmdb_info.get('title', 'Unknown')
    year = tmdb_info.get('year', 'Unknown')
    ext = file_path.split('.')[-1]
    
    final_dir = f"{destination_root}/{title} ({year})"
    final_path = f"{final_dir}/{title} ({year}).{ext}"
    
    if existing_file:
        # Compare logic
        pass # To be implemented fully with DB check
        
    return Decision(
        action="move",
        destination=final_path,
        reason="New processed file"
    )
