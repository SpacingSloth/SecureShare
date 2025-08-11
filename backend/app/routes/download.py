from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from app.core.database import get_db
from app.models.share_link import ShareLink
from app.models.file import File
from app.core.minio_client import minio_client
from fastapi.responses import StreamingResponse

router = APIRouter()

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