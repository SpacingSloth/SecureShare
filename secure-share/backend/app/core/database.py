from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from .config import settings

# Используем aiosqlite для асинхронной работы с SQLite
DATABASE_URL = "sqlite+aiosqlite:///./secureshare.db"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,  # Важно для SQLite
    echo=True  # Логирование запросов для отладки
)

# Правильное название - SessionLocal
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()

# Асинхронная функция для получения сессии
async def get_db():
    async with SessionLocal() as session:
        yield session