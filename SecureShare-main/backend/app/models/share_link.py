import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class ShareLink(Base):
    __tablename__ = "share_links"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String(36), ForeignKey("files.id"))
    token = Column(String(64), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    max_views = Column(Integer, default=1)
    views = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    file = relationship("File", back_populates="share_links")