from sqlalchemy import Column, Integer, String, Boolean, DateTime
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
