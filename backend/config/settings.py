import os
from pydantic import model_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Filearr"
    DEBUG: bool = True

    # Paths relative to container
    INPUT_DIR: str = "/media/downloads"
    OUTPUT_DIR: str = "/media/movies"
    DATA_DIR: str = "/data"

    # TMDB Settings
    TMDB_API_KEY: str = ""

    # Database (defaults to DATA_DIR/filearr.db)
    DATABASE_URL: str = ""

    # Clean up settings (Defaults derived from OUTPUT_DIR, can be overridden by env or DB)
    REJECTED_DIR: str = ""
    MOVIES_DIR: str = ""
    MALAYALAM_DIR: str = ""
    TV_DIR: str = ""
    MALAYALAM_TV_DIR: str = ""

    # Use a polling watcher instead of inotify (needed for SMB/NFS mounts)
    WATCHER_POLLING: bool = False

    # Ignore patterns (comma-separated glob patterns)
    IGNORE_PATTERNS: str = "*.sample,*.txt,*.nfo,*-RARBG*,*trailer*"

    class Config:
        env_file = ".env"

    @model_validator(mode="after")
    def derive_paths(self):
        # Computed after env loading so overriding DATA_DIR / OUTPUT_DIR propagates
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"sqlite:///{self.DATA_DIR}/filearr.db"
        if not self.REJECTED_DIR:
            self.REJECTED_DIR = os.path.join(self.OUTPUT_DIR, "rejected")
        if not self.MOVIES_DIR:
            self.MOVIES_DIR = self.OUTPUT_DIR
        if not self.MALAYALAM_DIR:
            self.MALAYALAM_DIR = os.path.join(self.OUTPUT_DIR, "malayalam-movies")
        if not self.TV_DIR:
            # Next to the movies folder, so movie libraries don't pick up episodes
            self.TV_DIR = os.path.join(os.path.dirname(self.OUTPUT_DIR.rstrip("/")), "tv-shows")
        if not self.MALAYALAM_TV_DIR:
            self.MALAYALAM_TV_DIR = os.path.join(self.TV_DIR, "malayalam-tv-shows")
        return self

settings = Settings()
