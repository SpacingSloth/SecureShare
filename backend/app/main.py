import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.database import Base, SessionLocal, engine
from app.core.minio_client import initialize_minio_bucket
from app.monitoring.setup import setup_monitoring
from app.routes import (
    admin,
    auth,
    download,
    files,
    share_links,
    share_links_compat,
    two_factor,
    ui,
    users,
)
from app.tasks.cleanup import start_cleanup_task

logger = logging.getLogger("secure-share")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            logger.info("Creating database tables:")
            for table in Base.metadata.tables.values():
                logger.info(f" - Table: {table.name}")
                for column in table.columns:
                    logger.info(f"    - Column: {column.name} ({column.type})")
            
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    try:
        initialize_minio_bucket()
        logger.info("MinIO initialized")
    except Exception as e:
        logger.error(f"MinIO initialization failed: {e}")
        raise

    cleanup_task = asyncio.create_task(start_cleanup_task())
    logger.info("Background cleanup task started")

    yield  

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        logger.info("Cleanup task cancelled")
    logger.info("Application shutdown complete")

app = FastAPI(
    title="SecureShare",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
    expose_headers=["Content-Disposition", "Content-Length"],
)

app.include_router(auth)
app.include_router(files)
app.include_router(share_links)
app.include_router(share_links_compat)  
app.include_router(users)
app.include_router(admin)
app.include_router(two_factor)
app.include_router(download)
app.include_router(ui)

from importlib import import_module

from fastapi import APIRouter as _APIRouter

_route_names = ["auth", "files", "share_links", "download", "users", "two_factor", "admin", "ui"]
for _name in _route_names:
    try:
        _mod = import_module(f"app.routes.{_name}")
        _router = getattr(_mod, "router", None)
        if isinstance(_router, _APIRouter):
            app.include_router(_router, prefix="/api")
        elif isinstance(_mod, _APIRouter):
            app.include_router(_mod, prefix="/api")
        else:
            _alt = getattr(_mod, _name, None)
            if isinstance(_alt, _APIRouter):
                app.include_router(_alt, prefix="/api")
    except Exception as _e:
        import logging as _logging
        _logging.getLogger("secure-share").warning("Failed to add /api-prefixed router for %s: %s", _name, _e)

setup_monitoring(app)

@app.get("/health")
async def health_check():
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
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