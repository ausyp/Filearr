import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Filearr"
    DEBUG: bool = True
    
    # Paths
    INPUT_DIR: str = "/input"
    OUTPUT_DIR: str = "/output"
    DATA_DIR: str = "/data"
    
    # TMDB Settings
    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
    
    # Database
    DATABASE_URL: str = f"sqlite:///{DATA_DIR}/filearr.db"
    
    # Clean up settings
    TRASH_DIR: str = f"{OUTPUT_DIR}/.trash"
    REJECTED_DIR: str = f"{OUTPUT_DIR}/.rejected"
    
    class Config:
        env_file = ".env"

settings = Settings()
