from sqlalchemy.orm import Session
from backend.db.models import SystemSetting
from backend.config.settings import settings as env_settings
from backend.db.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

class ConfigService:
    @staticmethod
    def get_setting(key: str, default: str = None) -> str:
        """
        Retrieves a setting. Priority:
        1. Database
        2. Environment Variable (via settings.py)
        3. Default value
        """
        db = SessionLocal()
        try:
            db_setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            if db_setting and db_setting.value:
                return db_setting.value
        except Exception as e:
            logger.error(f"Error retrieving setting {key}: {e}")
        finally:
            db.close()
            
        # Fallback to env settings
        if hasattr(env_settings, key):
            return getattr(env_settings, key)
            
        return default

    @staticmethod
    def set_setting(key: str, value: str):
        db = SessionLocal()
        try:
            setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            if not setting:
                setting = SystemSetting(key=key, value=value)
                db.add(setting)
            else:
                old_value = setting.value
                setting.value = value
                logger.info(f"Updated setting {key}: {old_value} -> {value}")
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving setting {key}: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    @staticmethod
    def get_all_settings():
        """
        Returns a dict of all settings (merged Env and DB).
        """
        # Start with env settings
        config = {
            "TMDB_API_KEY": env_settings.TMDB_API_KEY,
            "INPUT_DIR": env_settings.INPUT_DIR,
            "OUTPUT_DIR": env_settings.OUTPUT_DIR,
            "MOVIES_DIR": env_settings.MOVIES_DIR,
            "MALAYALAM_DIR": env_settings.MALAYALAM_DIR,
            "REJECTED_DIR": env_settings.REJECTED_DIR,
            "TRASH_DIR": env_settings.TRASH_DIR,
        }
        
        # Overlay DB settings
        try:
            db = SessionLocal()
            try:
                db_settings = db.query(SystemSetting).all()
                for s in db_settings:
                    if s.value:
                        config[s.key] = s.value
            except Exception as e:
                logger.error(f"Error querying DB settings: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error creating DB session in get_all_settings: {e}")
            
        return config

config_service = ConfigService()
