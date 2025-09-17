from pydantic import BaseModel, EmailStr, constr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class EmailVerificationRequest(BaseModel):
    user_id: str
    code: str

class TwoFactorVerification(BaseModel):
    user_id: str
    code: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: constr(min_length=8)

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    code: str
    new_password: constr(min_length=8)

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