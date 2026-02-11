"""
Ignore Service - Manages file ignore patterns for Filearr
"""
from backend.db.database import SessionLocal
from backend.db.models import SystemSetting
import fnmatch
import logging

logger = logging.getLogger(__name__)

class IgnoreService:
    
    @staticmethod
    def get_ignore_patterns() -> list[str]:
        """Get all ignore patterns from database"""
        db = SessionLocal()
        try:
            setting = db.query(SystemSetting).filter(SystemSetting.key == "IGNORE_PATTERNS").first()
            if setting and setting.value:
                # Split by comma and strip whitespace
                patterns = [p.strip() for p in setting.value.split(",") if p.strip()]
                return patterns
            return []
        except Exception as e:
            logger.error(f"Error retrieving ignore patterns: {e}")
            return []
        finally:
            db.close()
    
    @staticmethod
    def set_ignore_patterns(patterns: list[str]):
        """Set ignore patterns in database"""
        db = SessionLocal()
        try:
            # Join patterns with comma
            pattern_str = ",".join(patterns)
            
            setting = db.query(SystemSetting).filter(SystemSetting.key == "IGNORE_PATTERNS").first()
            if not setting:
                setting = SystemSetting(key="IGNORE_PATTERNS", value=pattern_str)
                db.add(setting)
            else:
                setting.value = pattern_str
            
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving ignore patterns: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def add_pattern(pattern: str) -> bool:
        """Add a new ignore pattern"""
        patterns = IgnoreService.get_ignore_patterns()
        if pattern not in patterns:
            patterns.append(pattern)
            return IgnoreService.set_ignore_patterns(patterns)
        return True
    
    @staticmethod
    def remove_pattern(pattern: str) -> bool:
        """Remove an ignore pattern"""
        patterns = IgnoreService.get_ignore_patterns()
        if pattern in patterns:
            patterns.remove(pattern)
            return IgnoreService.set_ignore_patterns(patterns)
        return True
    
    @staticmethod
    def should_ignore(file_path: str) -> tuple[bool, str]:
        """
        Check if file should be ignored based on patterns OR specific file list.
        Returns (should_ignore, reason)
        """
        import os
        from backend.db.models import IgnoredFile
        
        filename = os.path.basename(file_path)
        
        # Check specific ignored files first
        db = SessionLocal()
        try:
            ignored_file = db.query(IgnoredFile).filter(IgnoredFile.file_path == file_path).first()
            if ignored_file:
                return True, f"File manually ignored: {ignored_file.reason or 'No reason provided'}"
        except Exception as e:
            logger.error(f"Error checking ignored files: {e}")
        finally:
            db.close()
        
        # Check patterns
        patterns = IgnoreService.get_ignore_patterns()
        for pattern in patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True, f"Matched pattern: {pattern}"
        
        return False, ""
    
    @staticmethod
    def add_ignored_file(file_path: str, reason: str = None) -> bool:
        """Add a specific file to the ignore list"""
        import os
        from backend.db.models import IgnoredFile
        
        db = SessionLocal()
        try:
            # Check if already ignored
            existing = db.query(IgnoredFile).filter(IgnoredFile.file_path == file_path).first()
            if existing:
                return True
            
            ignored_file = IgnoredFile(
                file_path=file_path,
                filename=os.path.basename(file_path),
                reason=reason
            )
            db.add(ignored_file)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding ignored file: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def remove_ignored_file(file_path: str) -> bool:
        """Remove a specific file from the ignore list"""
        from backend.db.models import IgnoredFile
        
        db = SessionLocal()
        try:
            ignored_file = db.query(IgnoredFile).filter(IgnoredFile.file_path == file_path).first()
            if ignored_file:
                db.delete(ignored_file)
                db.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing ignored file: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    @staticmethod
    def get_ignored_files() -> list:
        """Get all specifically ignored files"""
        from backend.db.models import IgnoredFile
        
        db = SessionLocal()
        try:
            ignored_files = db.query(IgnoredFile).order_by(IgnoredFile.ignored_at.desc()).all()
            return [{
                "file_path": f.file_path,
                "filename": f.filename,
                "reason": f.reason,
                "ignored_at": f.ignored_at.isoformat()
            } for f in ignored_files]
        except Exception as e:
            logger.error(f"Error retrieving ignored files: {e}")
            return []
        finally:
            db.close()
    
    @staticmethod
    def test_pattern(pattern: str, filename: str) -> bool:
        """Test if a pattern matches a filename"""
        return fnmatch.fnmatch(filename, pattern)

ignore_service = IgnoreService()
