import os
import uuid
import tempfile
import logging
from fastapi import APIRouter, Depends, UploadFile, Request, BackgroundTasks, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.file import File
from app.models.share_link import ShareLink
from app.schemas.file import FileInfo, UploadResponse, ShareResponse
from app.services.file_service import process_uploaded_file
from app.core.minio_client import minio_client
from app.core.config import settings
from app.models.share_link import ShareLink
from datetime import datetime, timedelta

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile,
    expire_days: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Генерация уникального ключа для файла
    file_key = f"{uuid.uuid4()}_{file.filename}"
    content_type = file.content_type or "application/octet-stream"
    
    # Определение размера файла
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    
    # Создаем временный файл для обработки
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create temporary file: {str(e)}"
        )
    
    # Загрузка в MinIO
    try:
        with open(temp_path, 'rb') as file_data:
            minio_client.put_object(
                settings.MINIO_BUCKET,
                file_key,
                file_data,
                length=file_size,
                content_type=content_type
            )
    except Exception as e:
        os.unlink(temp_path)  # Удаляем временный файл при ошибке
        raise HTTPException(
            status_code=500, 
            detail=f"File upload failed: {str(e)}"
        )
    
    # Явно генерируем UUID как строку
    file_id = str(uuid.uuid4())
    
    # Сохранение метаданных в БД
    expires_at = datetime.utcnow() + timedelta(days=expire_days)
    db_file = File(
        id=file_id,  # Используем строковый UUID
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
    
    # Запуск фоновой задачи
    if process_uploaded_file and callable(process_uploaded_file):
        background_tasks.add_task(
            process_uploaded_file,
            tmp_path=temp_path,
            user_id=str(current_user.id),
            filename=file.filename,
            expire_days=expire_days,
            content_type=content_type
        )
    
    # Формирование URL для скачивания
    download_url = f"{request.base_url}download/{file_id}"
    
    return UploadResponse(
        id=file_id,  # Возвращаем строковый UUID
        filename=db_file.filename,
        content_type=db_file.content_type,
        size=db_file.size,
        download_url=download_url,
        expires_at=db_file.expires_at
    )

@router.get("/file/{file_id}", response_model=FileInfo)
async def get_file_info(
    file_id: str,  # Изменено на string вместо UUID
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Поиск файла по строковому ID
    result = await db.execute(select(File).where(File.id == file_id))
    file = result.scalars().first()
    
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
        download_url=f"/download/{file.id}"
    )

@router.get("/files", response_model=list[FileInfo])
async def list_files(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    search: str = Query(None)
):
    query = select(File).where(File.owner_id == current_user.id)
    
    if search:
        query = query.where(File.filename.contains(search))
    
    result = await db.execute(query)
    files = result.scalars().all()
    
    return [
        FileInfo(
            id=file.id,
            filename=file.filename,
            content_type=file.content_type,
            size=file.size,
            created_at=file.created_at,
            expires_at=file.expires_at,
            download_url=f"/download/{file.id}"
        )
        for file in files
    ]

@router.post("/files/{file_id}/share", response_model=ShareResponse)
async def share_file(
    request: Request,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Sharing file: {file_id}")
    
    # Ищем файл по ID
    result = await db.execute(select(File).where(File.id == file_id))
    file = result.scalars().first()
    
    if not file:
        logger.error(f"File not found: {file_id}")
        raise HTTPException(status_code=404, detail="File not found")
    
    # Проверяем права доступа
    if file.owner_id != current_user.id and not current_user.is_admin:
        logger.warning(f"Access denied for user {current_user.id} to file {file_id}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Генерируем уникальный токен для доступа
    share_token = str(uuid.uuid4())
    
    # Создаем запись в БД
    expires_at = datetime.utcnow() + timedelta(days=7)
    new_share_link = ShareLink(
        token=share_token,
        file_id=file_id,
        expires_at=expires_at,
        max_views=5,  # Пример: разрешаем 5 скачиваний
        is_active=True
    )
    
    await db.refresh(new_share_link)
    
    # Формируем URL для общего доступа
    share_url = f"{request.base_url}download/{share_token}"
    
    logger.info(f"Share URL created for file {file_id}: {share_url}")
    return ShareResponse(
        share_url=share_url,
        token=share_token,
        expires_at=expires_at
    )

@router.get("/download/{token}")
async def download_shared_file(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    # Ищем активную ссылку
    result = await db.execute(
        select(ShareLink)
        .where(ShareLink.token == token)
        .where(ShareLink.is_active == True)
    )
    share_link = result.scalars().first()
    
    if not share_link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    # Проверяем срок действия
    if share_link.expires_at < datetime.utcnow():
        share_link.is_active = False
        db.add(share_link)
        await db.commit()
        raise HTTPException(status_code=410, detail="Link expired")
    
    # Проверяем лимит скачиваний
    if share_link.views >= share_link.max_views:
        share_link.is_active = False
        db.add(share_link)
        await db.commit()
        raise HTTPException(status_code=410, detail="Download limit reached")
    
    # Ищем файл
    result = await db.execute(select(File).where(File.id == share_link.file_id))
    file = result.scalars().first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Увеличиваем счетчик просмотров
    share_link.views += 1
    if share_link.views >= share_link.max_views:
        share_link.is_active = False
    
    db.add(share_link)
    await db.commit()
    
    # Скачиваем файл из MinIO
    try:
        response = minio_client.get_object(
            file.bucket,
            file.object_name
        )
        
        return StreamingResponse(
            response.stream(32*1024),
            media_type=file.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={file.filename}"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"File download failed: {str(e)}"
        )
    finally:
        response.close()
        response.release_conn()