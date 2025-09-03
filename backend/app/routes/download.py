from datetime import datetime
from typing import Optional
import urllib.parse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
import anyio

from app.core.database import get_db
from app.core.minio_client import minio_client
from app.models.file import File
from app.models.share_link import ShareLink

router = APIRouter()

CHUNK_SIZE = 64 * 1024  # 64 KiB


def _close_minio_object(obj) -> None:
    # MinIO объект нужно закрыть и освободить коннект
    try:
        obj.close()
    except Exception:
        pass
    try:
        obj.release_conn()
    except Exception:
        pass


async def _aiter_minio(obj):
    """Безопасный для event loop асинхронный итератор по MinIO-объекту."""
    try:
        while True:
            chunk = await anyio.to_thread.run_sync(obj.read, CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
    finally:
        await anyio.to_thread.run_sync(_close_minio_object, obj)


@router.get("/download/{token}")
async def download_by_token(
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # 1) Находим шэр-ссылку по токену
    now = datetime.utcnow()  # в БД у тебя даты на вид naive → юзаем naive UTC
    res = await db.execute(select(ShareLink).where(ShareLink.token == token))
    link: Optional[ShareLink] = res.scalars().first()

    # Не палим наличие токена — одинаковый ответ
    if not link or not link.is_active or (link.expires_at and link.expires_at <= now):
        raise HTTPException(status_code=404, detail="File not found")

    # 2) Достаём файл
    res = await db.execute(select(File).where(File.id == link.file_id))
    file: Optional[File] = res.scalars().first()
    if not file:
        # если файла нет — деактивируем ссылку и отвечаем 404
        link.is_active = False
        await db.commit()
        raise HTTPException(status_code=404, detail="File not found")

    # 3) Фиксируем просмотр (до выдачи контента — чтобы не злоупотребляли)
    link.views = (link.views or 0) + 1
    if link.max_views and link.views >= link.max_views:
        link.is_active = False
    await db.commit()

    # 4) Узнаём размер/метаданные объекта (stat) и открываем поток
    try:
        stat = await run_in_threadpool(minio_client.stat_object, file.bucket, file.object_name)
    except Exception:
        # объект в хранилище отсутствует / недоступен
        raise HTTPException(status_code=404, detail="File not found")

    try:
        obj = await run_in_threadpool(minio_client.get_object, file.bucket, file.object_name)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

    # 5) Готовим заголовки и отдаём StreamingResponse
    filename = file.filename or file.object_name.rsplit("/", 1)[-1]
    # RFC 5987 для юникод-имён
    content_disposition = f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"

    headers = {
        "Content-Disposition": content_disposition,
        "Content-Length": str(stat.size),
        # Если фронт вытаскивает имя из заголовков — его надо экспозить (см. CORS ниже)
    }

    media_type = file.content_type or getattr(stat, "content_type", None) or "application/octet-stream"

    return StreamingResponse(
        _aiter_minio(obj),
        media_type=media_type,
        headers=headers,
    )
