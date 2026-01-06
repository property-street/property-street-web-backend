from sqlalchemy import create_engine
from contextlib import asynccontextmanager
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine

from . import env_is_test
from property_street_backend.config.settings import (
    DEBUG,
    DATABASE_URL, 
    TEST_DATABASE_URL, 
    PROD_DATABASE_URL,
)

Base = declarative_base()


def _get_database_url() -> str:
    if env_is_test():
        return TEST_DATABASE_URL
    return DATABASE_URL if DEBUG else PROD_DATABASE_URL


DATABASE_URL = _get_database_url()

async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
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




#==================================
# Synchronous Section
#==================================
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)