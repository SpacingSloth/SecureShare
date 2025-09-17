import asyncio
import logging
import os
from datetime import datetime

from sqlalchemy import and_, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.minio_client import minio_client
from app.models.file import File
from app.models.share_link import ShareLink
from app.monitoring.setup import report_cleanup

logger = logging.getLogger(__name__)

INTERVAL_SECS = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "300"))  
MAX_PER_LOOP = int(os.getenv("CLEANUP_MAX_RECORDS_PER_LOOP", "200"))
RETRY_ATTEMPTS = int(os.getenv("CLEANUP_RETRY_ATTEMPTS", "3"))
RETRY_BACKOFF = float(os.getenv("CLEANUP_RETRY_BACKOFF_SECS", "0.5"))

CLEANED_FILES = 0
CLEANED_LINKS = 0
FAILED_FILE_DELETES = 0

async def _retry_minio_delete(bucket: str, object_name: str) -> bool:
    """Retry wrapper for MinIO deletion."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            minio_client.remove_object(bucket, object_name)
            return True
        except Exception as e:
            logger.warning(f"MinIO delete failed (attempt {attempt}/{RETRY_ATTEMPTS}) "
                           f"bucket={bucket} object={object_name} err={e}")
            if attempt < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF * attempt)
    return False

async def cleanup_expired_files():
    global CLEANED_FILES, CLEANED_LINKS, FAILED_FILE_DELETES
    logger.info("Cleanup task started: interval=%s max_per_loop=%s", INTERVAL_SECS, MAX_PER_LOOP)

    while True:
        started = datetime.utcnow()
        files_deleted = 0
        links_deactivated = 0

        try:
            async with SessionLocal() as db:  
                now = datetime.utcnow()

                res = await db.execute(
                    select(ShareLink).where(
                        and_(ShareLink.is_active == True, ShareLink.expires_at != None, ShareLink.expires_at < now)
                    ).limit(MAX_PER_LOOP)
                )
                expired_links = res.scalars().all()
                if expired_links:
                    for link in expired_links:
                        link.is_active = False
                        links_deactivated += 1
                    await db.commit()

                res = await db.execute(
                    select(File).where(
                        File.expires_at != None, File.expires_at < now
                    ).limit(MAX_PER_LOOP)
                )
                files_to_delete = res.scalars().all()

                for f in files_to_delete:
                    ok = await _retry_minio_delete(f.bucket or settings.MINIO_BUCKET, f.object_name)
                    if ok:
                        await db.delete(f)
                        files_deleted += 1
                    else:
                        FAILED_FILE_DELETES += 1
                        logger.error("Failed to delete object from MinIO after retries: %s", f.object_name)

                if files_to_delete:
                    await db.commit()

            CLEANED_FILES += files_deleted
            CLEANED_LINKS += links_deactivated

            duration = (datetime.utcnow() - started).total_seconds()
            report_cleanup(files_deleted, links_deactivated, FAILED_FILE_DELETES, duration)
            logger.info("cleanup_summary files_deleted=%s links_deactivated=%s failed_minio=%s duration=%.3fs total_files=%s total_links=%s",
                        files_deleted, links_deactivated, FAILED_FILE_DELETES, duration, CLEANED_FILES, CLEANED_LINKS)

            await asyncio.sleep(INTERVAL_SECS)

        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled by shutdown")
            raise
        except Exception as e:
            logger.exception("Cleanup loop error: %s", e)
            await asyncio.sleep(min(60, INTERVAL_SECS))

async def start_cleanup_task():
    return await cleanup_expired_files()