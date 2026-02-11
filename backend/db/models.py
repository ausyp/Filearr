from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from backend.db.database import Base
from datetime import datetime

class ProcessedFile(Base):
    __tablename__ = "processed_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    original_path = Column(String)
    destination_path = Column(String)
    movie_name = Column(String)
    year = Column(String)
    language = Column(String)
    quality_score = Column(Integer)
    action = Column(String) # move, reject, replace
    created_at = Column(DateTime, default=datetime.utcnow)

class RejectedFile(Base):
    __tablename__ = "rejected_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ErrorLog(Base):
    __tablename__ = "error_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String)  # ERROR, WARNING, INFO
    source = Column(String)  # watcher, cleanup, api, processor
    message = Column(String)
    traceback = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CleanupLog(Base):
    __tablename__ = "cleanup_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    operation_type = Column(String)  # scan, move, delete, dry_run
    file_path = Column(String)
    destination = Column(String, nullable=True)
    status = Column(String)  # success, failed, skipped
    details = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class WatcherLog(Base):
    __tablename__ = "watcher_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String)  # created, moved, modified
    file_path = Column(String)
    action = Column(String)  # detected, processed, ignored, failed
    reason = Column(String, nullable=True)  # ignore reason or error message
    created_at = Column(DateTime, default=datetime.utcnow)

class IgnoredFile(Base):
    __tablename__ = "ignored_files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, index=True)
    filename = Column(String)
    reason = Column(String, nullable=True)  # User-provided reason
    ignored_at = Column(DateTime, default=datetime.utcnow)
