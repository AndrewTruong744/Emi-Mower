from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config.settings import settings

# Create database engine for async PostgreSQL connection
# echo=True prints SQL statements to console, which is helpful during local development
engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,
    echo=True,
    future=True,
)

# Create a sessionmaker that yields AsyncSession objects
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for defining database models
class Base(DeclarativeBase):
    pass

# FastAPI dependency to yield database sessions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
