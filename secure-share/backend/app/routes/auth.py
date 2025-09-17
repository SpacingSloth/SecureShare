import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from app.core.database import get_db
from app.core.security import create_access_token, verify_password, get_password_hash, get_current_user
from app.utils.email import send_email, generate_verification_code, store_verification_code, verify_code
from app.schemas.user import UserCreate, Token, EmailVerificationRequest, TwoFactorVerification, PasswordChange, PasswordResetRequest, PasswordResetConfirm
from app.models.user import User


router = APIRouter()

# Получаем значения из переменных окружения
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
EMAIL_VERIFICATION_ENABLED = os.getenv('EMAIL_VERIFICATION_ENABLED', 'false').lower() == 'true'
TWO_FACTOR_EMAIL_ENABLED = os.getenv('TWO_FACTOR_EMAIL_ENABLED', 'false').lower() == 'true'

@router.post("/register", response_model=dict)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем существование пользователя
    result = await db.execute(select(User).filter(User.email == user.email))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Создаем нового пользователя
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email, 
        hashed_password=hashed_password,
        email_verified=not EMAIL_VERIFICATION_ENABLED  # Если проверка отключена, считаем email подтвержденным
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # Если включена проверка email, отправляем verification code
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
    
    # Если проверка email отключена, сразу возвращаем токен
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/verify-email", response_model=Token)
async def verify_email(request: EmailVerificationRequest, db: AsyncSession = Depends(get_db)):
    # Проверяем код подтверждения
    if not verify_code(request.user_id, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # Находим пользователя и отмечаем email как подтвержденный
    result = await db.execute(select(User).filter(User.id == request.user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.email_verified = True
    await db.commit()
    
    # Создаем токен доступа
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # Ищем пользователя
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalars().first()
    
    # Проверяем учетные данные
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверяем, подтвержден ли email
    if EMAIL_VERIFICATION_ENABLED and not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified. Please check your email for verification instructions.",
        )
    
    # Если включена 2FA, отправляем код и возвращаем информацию о необходимости 2FA
    if user.two_factor_enabled and TWO_FACTOR_EMAIL_ENABLED:
        verification_code = generate_verification_code()
        store_verification_code(user.id, verification_code)
        
        await send_email(
            to_email=user.email,
            subject="Your SecureShare 2FA Code",
            body=f"Your two-factor authentication code is: {verification_code}"
        )
        
     #  raise HTTPException(
     #      status_code=status.HTTP_202_ACCEPTED,
     #      detail="Two-factor authentication required",
     #      headers={"X-2FA-Required": "true", "X-User-ID": str(user.id)},
     #  )
    
            # Возвращаем JSON ответ с статусом 202 и user_id в теле
        return JSONResponse(
            status_code=202,
            content={
                "message": "Two-factor authentication required",
                "user_id": user.id
            }
        )
    
    # Создаем токен доступа
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/verify-2fa", response_model=Token)
async def verify_two_factor(request: TwoFactorVerification, db: AsyncSession = Depends(get_db)):
    # Проверяем код 2FA
    if not verify_code(request.user_id, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # Находим пользователя
    result = await db.execute(select(User).filter(User.id == request.user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Создаем токен доступа
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
    # Проверяем текущий пароль
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Проверяем, что новый пароль отличается от текущего
    if verify_password(password_data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Хэшируем новый пароль
    new_hashed_password = get_password_hash(password_data.new_password)
    current_user.hashed_password = new_hashed_password
    
    # Обновляем запись в базе данных
    await db.commit()
    
    return {"message": "Password changed successfully"}

@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    # Ищем пользователя по email
    result = await db.execute(select(User).filter(User.email == request.email))
    user = result.scalars().first()
    
    if not user:
        # Для безопасности не сообщаем, что email не зарегистрирован
        return {"message": "If the email is registered, you will receive a reset code"}
    
    # Генерируем код сброса пароля
    reset_code = generate_verification_code()
    store_verification_code(f"password_reset:{user.id}", reset_code)
    
    # Отправляем email с кодом
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
    # Ищем пользователя по email
    result = await db.execute(select(User).filter(User.email == request.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Проверяем код сброса
    if not verify_code(f"password_reset:{user.id}", request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )
    
    # Хэшируем новый пароль
    new_hashed_password = get_password_hash(request.new_password)
    user.hashed_password = new_hashed_password
    
    # Обновляем запись в базе данных
    await db.commit()
    
    return {"message": "Password reset successfully"}