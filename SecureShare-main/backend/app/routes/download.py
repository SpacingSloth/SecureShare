from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from starlette.background import BackgroundTask
from fastapi.responses import StreamingResponse

from app.core.database import get_db
from app.models.share_link import ShareLink
from app.models.file import File
from app.core.minio_client import minio_client

router = APIRouter()

@router.get("/download/{token}")
async def download_by_token(token: str, db: AsyncSession = Depends(get_db)):
    # 1) ищем активную ссылку
    result = await db.execute(
        select(ShareLink).where(ShareLink.token == token, ShareLink.is_active == True)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # 2) проверяем срок жизни
    if link.expires_at and link.expires_at <= datetime.utcnow():
        link.is_active = False
        await db.commit()
        raise HTTPException(status_code=410, detail="Link expired")

    # 3) берём файл
    result = await db.execute(select(File).where(File.id == link.file_id))
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # 4) получаем объект из MinIO
    obj = minio_client.get_object(file.bucket, file.object_name)

    # 5) учёт просмотров и авто-деактивация по лимиту
    link.views = (link.views or 0) + 1
    if link.max_views and link.views >= link.max_views:
        link.is_active = False
    await db.commit()

    # 6) аккуратное закрытие объекта после отправки
    bg = BackgroundTask(lambda: (obj.close(), obj.release_conn()))

    return StreamingResponse(
        obj.stream(64 * 1024),
        media_type=file.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file.filename}"'},
        background=bg,
    )
