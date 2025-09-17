from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

@router.get("/")
async def admin_dashboard(current_user: User = Depends(get_current_user)):
    # Проверка прав администратора
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"message": "Admin dashboard"}