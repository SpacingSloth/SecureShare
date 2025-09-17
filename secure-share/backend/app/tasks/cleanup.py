import asyncio
from datetime import datetime, timedelta
from sqlalchemy.sql import text
from app.core.database import SessionLocal
from app.models.file import File
from app.models.share_link import ShareLink
from app.core.minio_client import minio_client
from app.core.config import settings
import logging
from minio.error import S3Error

logger = logging.getLogger("secure-share")

async def cleanup_expired_files():
    while True:
        try:
            now = datetime.utcnow()
            logger.info(f"Starting cleanup at {now}")
            
            async with SessionLocal() as db:
                # Деактивация просроченных ссылок
                expired_links = await db.execute(
                    text("""
                    UPDATE share_links 
                    SET is_active = 'N'
                    WHERE is_active = 'Y' AND expires_at < :now
                    """),
                    {"now": now}
                )
                logger.info(f"Deactivated {expired_links.rowcount} expired links")
                
                # Удаление файлов без активных ссылок
                expired_files = await db.execute(
                    text("""
                    SELECT * FROM files 
                    WHERE expires_at < :now
                    AND id NOT IN (
                        SELECT file_id FROM share_links 
                        WHERE is_active = 'Y'
                    )
                    """),
                    {"now": now}
                )
                files_to_delete = expired_files.scalars().all()
                
                for file in files_to_delete:
                    try:
                        minio_client.remove_object(
                            settings.MINIO_BUCKET, 
                            file.s3_key
                        )
                        logger.info(f"Deleted file from MinIO: {file.s3_key}")
                        await db.delete(file)  # <-- Удаляем только при успешном удалении из MinIO
                    except S3Error as e:
                        if e.code == "NoSuchKey":
                            logger.warning(f"File already missing in MinIO: {file.s3_key}")
                            await db.delete(file)  # Удаляем запись если файла нет в хранилище
                        else:
                            logger.error(f"MinIO error for {file.s3_key}: {e}")
                    except Exception as e:
                        logger.error(f"Failed to process file {file.s3_key}: {e}")
                
                await db.commit()
                logger.info(f"Processed {len(files_to_delete)} expired files")
            
            # Пауза между проверками
            await asyncio.sleep(600)
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            await asyncio.sleep(60)

async def start_cleanup_task():
    try:
        await cleanup_expired_files()
    except asyncio.CancelledError:
        logger.info("Cleanup task cancelled")
        raise