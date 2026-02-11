import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Filearr"
    DEBUG: bool = True
    
    # Paths
    # Paths relative to container
    INPUT_DIR: str = "/media/downloads"
    OUTPUT_DIR: str = "/media/movies"
    DATA_DIR: str = "/data"
    
    # TMDB Settings
    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
    
    # Database
    DATABASE_URL: str = f"sqlite:///{DATA_DIR}/filearr.db"
    
    # Clean up settings (Defaults, can be overridden by env or DB)
    TRASH_DIR: str = os.getenv("TRASH_DIR", f"{OUTPUT_DIR}/.trash")
    REJECTED_DIR: str = os.getenv("REJECTED_DIR", f"{OUTPUT_DIR}/.rejected")
    MOVIES_DIR: str = os.getenv("MOVIES_DIR", f"{OUTPUT_DIR}/movies")
    MALAYALAM_DIR: str = os.getenv("MALAYALAM_DIR", f"{OUTPUT_DIR}/malayalam-movies")
    
    class Config:
        env_file = ".env"

settings = Settings()
