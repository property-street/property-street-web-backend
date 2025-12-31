from contextlib import asynccontextmanager
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine

from . import get_env
from property_street_backend.config.settings import (
    DEBUG,
    DATABASE_URL, 
    TEST_DATABASE_URL, 
    PROD_DATABASE_URL,
)

Base = declarative_base()


def _get_database_url() -> str:
    if get_env() == "test":
        return TEST_DATABASE_URL
    return DATABASE_URL if DEBUG else PROD_DATABASE_URL


DATABASE_URL = _get_database_url()

async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    max_overflow=10,
    pool_timeout=30,
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
) 

def get_async_session():
    return AsyncSessionLocal

@asynccontextmanager
async def get_postgres_instance():
    async with AsyncSessionLocal() as session:
        try:
            yield session  
        finally:
            await session.close()