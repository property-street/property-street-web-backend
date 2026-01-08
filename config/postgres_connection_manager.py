from sqlalchemy import create_engine
from contextlib import asynccontextmanager
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from property_street_backend.app.initiator import logger

from . import env_is_test
from property_street_backend.config.settings import (
    DEBUG,
    DEV_DATABASE_URL, 
    TEST_DATABASE_URL, 
    PROD_DATABASE_URL,
)

Base = declarative_base()


def get_database_url() -> str:
    if env_is_test():
        return TEST_DATABASE_URL
    return DEV_DATABASE_URL if DEBUG else PROD_DATABASE_URL

DATABASE_URL = get_database_url()

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
    async_session_local = get_async_session()
    async with async_session_local() as session:
        try:
            yield session  
        finally:
            await session.close()

def runtime_async_engine():
    database_url = get_database_url()
    return create_async_engine(
        database_url, echo=False, max_overflow=10, pool_timeout=30
    ) 

def runtime_async_session_maker():
    async_engine = runtime_async_engine()
    AsyncSessionMaker = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    ) 
    return AsyncSessionMaker



#==================================
# Synchronous Section
#==================================
def runtime_sync_session_maker():
    URL = get_database_url()
    SYNC_DATABASE_URL = URL.replace("+asyncpg", "")
    sync_engine = create_engine(
        SYNC_DATABASE_URL, echo=False, pool_pre_ping=True, future=True,
    )
    return sessionmaker(
        bind=sync_engine, autocommit=False, autoflush=False,
    )