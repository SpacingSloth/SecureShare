import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class File(Base):
    __tablename__ = "files"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, index=True)
    content_type = Column(String)
    size = Column(Integer)
    owner_id = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    bucket = Column(String)
    object_name = Column(String)
    
    share_links = relationship("ShareLink", back_populates="file", cascade="all, delete-orphan")