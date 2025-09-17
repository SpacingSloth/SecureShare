import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    email_verified = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String, nullable=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    force_password_reset = Column(Boolean, default=False)
    is_2fa_enabled = Column(Boolean, default=False)
    otp_secret = Column(String, nullable=True)