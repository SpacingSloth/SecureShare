import os
import uuid
import tempfile
import logging
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, Request, BackgroundTasks, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select  # <-- используем единообразно sqlalchemy.select

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.file import File
from app.models.share_link import ShareLink
from app.schemas.file import FileInfo, UploadResponse, ShareResponse
from app.services.file_service import process_uploaded_file
from app.core.minio_client import minio_client
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    request: Request,  # можно уже не использовать, но оставим
    file: UploadFile,
    expire_days: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    file_key = f"{uuid.uuid4()}_{file.filename}"
    content_type = file.content_type or "application/octet-stream"

    # определяем размер до чтения
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    # пишем во временный файл (если нужен пост-процессинг)
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create temporary file: {e}")

    # грузим в MinIO
    try:
        with open(temp_path, "rb") as file_data:
            minio_client.put_object(
                settings.MINIO_BUCKET,
                file_key,
                file_data,
                length=file_size,
                content_type=content_type
            )
    except Exception as e:
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")

    # метаданные — БЕЗ ручного id; он проставится моделью
    expires_at = datetime.utcnow() + timedelta(days=expire_days)
    db_file = File(
        filename=file.filename,
        content_type=content_type,
        size=file_size,
        owner_id=current_user.id,
        bucket=settings.MINIO_BUCKET,
        object_name=file_key,
        expires_at=expires_at
    )

    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)

    # фоновая задача (если реально используется)
    if process_uploaded_file and callable(process_uploaded_file):
        background_tasks.add_task(
            process_uploaded_file,
            tmp_path=temp_path,
            user_id=str(current_user.id),
            filename=file.filename,
            expire_days=expire_days,
            content_type=content_type
        )
    else:
        # если пост-процессинг не нужен — удаляем временный файл
        try:
            os.unlink(temp_path)
        except Exception:
            pass

    # ВОЗВРАЩАЕМ без download_url
    return UploadResponse(
        id=db_file.id,
        filename=db_file.filename,
        content_type=db_file.content_type,
        size=db_file.size,
        expires_at=db_file.expires_at
    )

@router.get("/file/{file_id}", response_model=FileInfo)
async def get_file_info(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(File).where(File.id == file_id))
    file = result.scalar_one_or_none()
    if not file:
        logger.error(f"File not found: {file_id}")
        raise HTTPException(status_code=404, detail="File not found")

    if file.owner_id != current_user.id and not current_user.is_admin:
        logger.warning(f"Access denied for user {current_user.id} to file {file_id}")
        raise HTTPException(status_code=403, detail="Access denied")

    return FileInfo(
        id=file.id,
        filename=file.filename,
        content_type=file.content_type,
        size=file.size,
        created_at=file.created_at,
        expires_at=file.expires_at,
    )

@router.get("/files", response_model=list[FileInfo])
async def list_files(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(None)
):
    query = select(File).where(File.owner_id == current_user.id)
    if search:
        query = query.where(File.filename.contains(search))

    result = await db.execute(query)
    files = result.scalars().all()

    return [
        FileInfo(
            id=f.id,
            filename=f.filename,
            content_type=f.content_type,
            size=f.size,
            created_at=f.created_at,
            expires_at=f.expires_at,
        )
        for f in files
    ]

@router.post("/files/{file_id}/share", response_model=ShareResponse)
async def create_share_link(
    file_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(File).where(File.id == file_id))
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if file.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    token = secrets.token_urlsafe(24)
    expires_at = datetime.utcnow() + timedelta(days=7)

    link = ShareLink(
        file_id=file.id,
        token=token,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        max_views=5,
        views=0,
        is_active=True,
    )

    db.add(link)
    await db.commit()
    await db.refresh(link)

    scheme = request.headers.get("X-Forwarded-Proto") or request.url.scheme
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host")
    if not host:
        host = request.url.hostname
        if request.url.port:
            host = f"{host}:{request.url.port}"
    share_url = f"{scheme}://{host}/download/{token}"

    return ShareResponse(share_url=share_url, token=token, expires_at=expires_at)
