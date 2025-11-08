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

def get_async_session():
    env_is_test = get_env() == 'test'
    database_url = TEST_DATABASE_URL if env_is_test else (DATABASE_URL if DEBUG else PROD_DATABASE_URL)

    async_engine = create_async_engine(database_url, echo=False) # create engine (it manages a connection pool internally)

    # create a session, store its reference and increment the active connections
    SessionMaker = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    ) 

    return SessionMaker

@asynccontextmanager
async def get_postgres_instance():
    SessionLocal: sessionmaker = get_async_session()

    async with SessionLocal() as session:
        yield session

async def get_db():
    return get_postgres_instance()
