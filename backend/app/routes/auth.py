import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.schemas.user import (
    EmailVerificationRequest,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    Token,
    TwoFactorVerification,
    UserCreate,
)
from app.utils.email import (
    generate_verification_code,
    send_email,
    store_verification_code,
    verify_code,
)

router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
EMAIL_VERIFICATION_ENABLED = os.getenv('EMAIL_VERIFICATION_ENABLED', 'false').lower() == 'true'
TWO_FACTOR_EMAIL_ENABLED = os.getenv('TWO_FACTOR_EMAIL_ENABLED', 'false').lower() == 'true'

@router.post("/register", response_model=dict)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == user.email))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email, 
        hashed_password=hashed_password,
        email_verified=not EMAIL_VERIFICATION_ENABLED  
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    if EMAIL_VERIFICATION_ENABLED:
        verification_code = generate_verification_code()
        store_verification_code(db_user.id, verification_code)
        
        await send_email(
            to_email=user.email,
            subject="Verify your email for SecureShare",
            body=f"Your verification code is: {verification_code}"
        )
        
        return {
            "message": "Registration successful. Please check your email for verification code.",
            "user_id": db_user.id,
            "requires_verification": True
        }
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/verify-email", response_model=Token)
async def verify_email(request: EmailVerificationRequest, db: AsyncSession = Depends(get_db)):
    if not verify_code(request.user_id, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    result = await db.execute(select(User).filter(User.id == request.user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.email_verified = True
    await db.commit()
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if EMAIL_VERIFICATION_ENABLED and not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified. Please check your email for verification instructions.",
        )
    
    if user.two_factor_enabled and TWO_FACTOR_EMAIL_ENABLED:
        verification_code = generate_verification_code()
        store_verification_code(user.id, verification_code)
        
        await send_email(
            to_email=user.email,
            subject="Your SecureShare 2FA Code",
            body=f"Your two-factor authentication code is: {verification_code}"
        )   
        
        return JSONResponse(
            status_code=202,
            content={
                "message": "Two-factor authentication required",
                "user_id": user.id
            }
        )
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/verify-2fa", response_model=Token)
async def verify_two_factor(request: TwoFactorVerification, db: AsyncSession = Depends(get_db)):
    if not verify_code(request.user_id, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    result = await db.execute(select(User).filter(User.id == request.user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    if verify_password(password_data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    new_hashed_password = get_password_hash(password_data.new_password)
    current_user.hashed_password = new_hashed_password
    
    await db.commit()
    
    return {"message": "Password changed successfully"}

@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).filter(User.email == request.email))
    user = result.scalars().first()
    
    if not user:
        return {"message": "If the email is registered, you will receive a reset code"}
    
    reset_code = generate_verification_code()
    store_verification_code(f"password_reset:{user.id}", reset_code)
    
    await send_email(
        to_email=user.email,
        subject="Password Reset Code for SecureShare",
        body=f"Your password reset code is: {reset_code}"
    )
    
    return {"message": "If the email is registered, you will receive a reset code"}

@router.post("/reset-password")
async def reset_password(
    request: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).filter(User.email == request.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not verify_code(f"password_reset:{user.id}", request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )
    
    new_hashed_password = get_password_hash(request.new_password)
    user.hashed_password = new_hashed_password
    
    await db.commit()
    
    return {"message": "Password reset successfully"}