from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import User
from app.core.security import get_current_user

router = APIRouter()

@router.post("/enable-2fa")
async def enable_two_factor(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.two_factor_enabled = True
    await db.commit()
    return {"message": "Two-factor authentication enabled", "enabled": True}

@router.post("/disable-2fa")
async def disable_two_factor(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.two_factor_enabled = False
    await db.commit()
    return {"message": "Two-factor authentication disabled", "enabled": False}

@router.get("/2fa-status")
async def get_2fa_status(
    current_user: User = Depends(get_current_user)
):
    return {"two_factor_enabled": current_user.two_factor_enabled}