from __future__ import annotations

import os
import uuid
import tempfile
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, Request, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import aliased

from app.core.database import get_db
from app.core.config import settings
from app.core.minio_client import minio_client
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.file import File
from app.models.share_link import ShareLink
from app.schemas.file import FileInfo, UploadResponse, ShareResponse, FileListResponse
from app.utils.urls import build_external_url

logger = logging.getLogger("secure-share")

router = APIRouter(tags=["Files"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile,
    expire_days: int = Query(7, ge=1, le=365),
    create_share: bool = Query(False, description="Return share_url/token in UploadResponse"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1) Сохраняем во временный файл, чтобы получить размер/стрим
    suffix = ("_" + file.filename) if file.filename else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)
        temp_path = tmp.name

    file_size = os.path.getsize(temp_path)
    content_type = file.content_type or "application/octet-stream"
    object_name = f"{uuid.uuid4()}_{file.filename or 'upload.bin'}"

    # 2) Грузим в MinIO
    try:
        with open(temp_path, "rb") as fp:
            minio_client.put_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name,
                data=fp,
                length=file_size,
                content_type=content_type,
            )
    except Exception as e:
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass

    # 3) Пишем метаданные в БД
    expires_at = datetime.utcnow() + timedelta(days=expire_days)
    db_file = File(
        filename=file.filename or "upload.bin",
        content_type=content_type,
        size=file_size,
        owner_id=current_user.id,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        bucket=settings.MINIO_BUCKET,
        object_name=object_name,
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)

    share_url: Optional[str] = None
    token: Optional[str] = None

    # 4) По запросу — сразу создаём шар-ссылку
    if create_share:
        token = secrets.token_urlsafe(24)
        link = ShareLink(
            file_id=str(db_file.id),
            token=token,
            expires_at=expires_at,
            is_active=True,
        )
        db.add(link)
        await db.commit()
        await db.refresh(link)
        share_url = build_external_url(request, f"/s/{token}")

    # 5) Возвращаем UploadResponse (+share_url/token при необходимости)
    return UploadResponse(
        id=db_file.id,
        filename=db_file.filename,
        content_type=db_file.content_type,
        size=db_file.size,
        expires_at=db_file.expires_at,
        share_url=share_url,
        token=token,
    )


@router.get("/files/{file_id}", response_model=FileInfo)
async def get_file_info(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(select(File).where(File.id == str(file_id)))
    file = res.scalars().first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    if file.owner_id != current_user.id and not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Access denied")
    return FileInfo(
        id=file.id,
        filename=file.filename,
        content_type=file.content_type,
        size=file.size,
        created_at=file.created_at,
        expires_at=file.expires_at,
    )


@router.get("/files", response_model=FileListResponse)
async def list_files(
    search: Optional[str] = Query(None, description="Search by filename"),
    file_type: Optional[str] = Query(None, description="Filter by file extension (e.g., 'pdf', 'jpg')"),
    start_date: Optional[str] = Query(None, description="Filter by creation date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by creation date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Базовый запрос для файлов пользователя
    query = select(File).where(File.owner_id == current_user.id)
    
    # Поиск по имени файла
    if search and search.strip():
        query = query.where(File.filename.ilike(f"%{search.strip()}%"))
    
    # Фильтр по типу файла (расширению)
    if file_type:
        # Добавляем точку к расширению, если её нет
        if not file_type.startswith('.'):
            file_type = f".{file_type}"
        query = query.where(File.filename.ilike(f"%{file_type}"))
    
    # Фильтр по дате создания
    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(File.created_at >= start_datetime)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD.")
    
    if end_date:
        try:
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.where(File.created_at < end_datetime)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD.")
    
    # Получаем общее количество файлов (до пагинации)
    count_query = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_query)).scalar()
    
    # Добавляем сортировку и пагинацию
    query = query.order_by(File.created_at.desc()).offset(skip).limit(limit)
    
    # Выполняем запрос
    res = await db.execute(query)
    rows = res.scalars().all()
    
    # Формирование ответа
    files = [FileInfo.from_orm(f) for f in rows]
    total_count = await get_total_count(db, current_user.id, search, file_type, start_date, end_date)
    
    return FileListResponse(
        files=files,
        total=total_count,
        skip=skip,
        limit=limit
    )