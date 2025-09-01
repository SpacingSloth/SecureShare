from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime
    is_active: bool
    is_admin: bool
    force_password_reset: bool
    is_2fa_enabled: bool
    
    class Config:
        orm_mode = True

# Дополнительные схемы, которые могут пригодиться
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    force_password_reset: Optional[bool] = None

class UserInDB(UserResponse):
    hashed_password: str