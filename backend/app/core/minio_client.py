from minio import Minio
from minio.error import S3Error
import logging
from .config import settings

logger = logging.getLogger("secure-share")

minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False
)

def initialize_minio_bucket():
    try:
        if not minio_client.bucket_exists(settings.MINIO_BUCKET):
            minio_client.make_bucket(settings.MINIO_BUCKET)
            logger.info(f"Bucket '{settings.MINIO_BUCKET}' created successfully")
        else:
            logger.info(f"Bucket '{settings.MINIO_BUCKET}' already exists")
    except S3Error as e:
        logger.error(f"MinIO error: {e}")
        raise RuntimeError(f"Failed to initialize MinIO bucket: {e}")