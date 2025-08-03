import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession
)
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@db:5432/property_street_store"

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

async def test_connection():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()  # Fetch the first scalar result
        print(value)

if __name__ == "__main__":
    asyncio.run(test_connection())