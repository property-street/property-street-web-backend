import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from property_street_backend.config.settings import DATABASE_URL

# Async SQLAlchemy engine
async_engine = create_async_engine(DATABASE_URL, echo=False)

# Async SQLAlchemy session
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()

async def drop_metadata():
    async with async_engine.begin() as conn:
        # Drop the schema after tests
        await conn.run_sync(Base.metadata.drop_all)
        print("***torn down the Base's metadata")

if __name__ == "__main__":
    asyncio.run(drop_metadata())
