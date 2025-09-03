import uvicorn
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.database import Base, engine, SessionLocal
from app.core.minio_client import initialize_minio_bucket
from app.routes import auth, files, share_links, users, admin
from app.routes import download
from app.tasks.cleanup import start_cleanup_task
from app.monitoring.setup import setup_monitoring
from app.models import file, share_link, user

logger = logging.getLogger("secure-share")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Инициализация базы данных
    try:
        async with engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            # Логирование информации о создаваемых таблицах
            logger.info("Creating database tables:")
            for table in Base.metadata.tables.values():
                logger.info(f" - Table: {table.name}")
                for column in table.columns:
                    logger.info(f"    - Column: {column.name} ({column.type})")
            
            # Создание таблиц
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # 2. Инициализация MinIO
    try:
        initialize_minio_bucket()
        logger.info("MinIO initialized")
    except Exception as e:
        logger.error(f"MinIO initialization failed: {e}")
        raise

    # 3. Запуск фоновой задачи очистки
    cleanup_task = asyncio.create_task(start_cleanup_task())
    logger.info("Background cleanup task started")

    yield  # Приложение работает здесь

    # 4. Остановка приложения
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        logger.info("Cleanup task cancelled")
    logger.info("Application shutdown complete")

# Создание экземпляра FastAPI
app = FastAPI(
    title="SecureShare",
    version="1.0.0",
    lifespan=lifespan
)

# Добавление CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешает все источники (для разработки)
    allow_credentials=True,
    allow_methods=["*"],  # Разрешает все методы
    allow_headers=["*"],  # Разрешает все заголовки
)

# Подключение маршрутов
app.include_router(auth)
app.include_router(files)
app.include_router(users)
app.include_router(admin)
app.include_router(download.router)

# Настройка мониторинга
setup_monitoring(app)

@app.get("/health")
async def health_check():
    # Проверка подключения к БД
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Проверка подключения к MinIO
    try:
        from app.core.minio_client import minio_client
        minio_client.list_buckets()
        minio_status = "ok"
    except Exception as e:
        minio_status = f"error: {str(e)}"
    
    return {
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "storage": minio_status
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        timeout_keep_alive=60,
        limit_concurrency=100
    )