import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport
from pystyle import Colors
import redis.asyncio as redis

from property_street_backend.app.database import Base, get_db
from property_street_backend.app.initiator import redis_client
from property_street_backend.app.main import app
from property_street_backend.config.settings import (
    TEST_DATABASE_URL, 
    REDIS_CACHE_DB,
)
from property_street_backend.app.utils.store import email_verification_code_ttl

# Async SQLAlchemy engine and session for testing
# async_engine: An asynchronous SQLAlchemy engine created using create_async_engine for the test database.
# TestingSessionLocal: An asynchronous session factory created using sessionmaker with AsyncSession.

test_async_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
# Async SQLAlchemy session for testing
AsyncTestSessionLocal = sessionmaker(
    bind=test_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Minimal Dependency structure to get async test DB session
@pytest.fixture(scope="function")
async def get_test_db__fixture(
    request,
    event_loop,
):
    async with test_async_engine.begin() as conn:
        # Create the database schema
        await conn.run_sync(Base.metadata.create_all)
        print("***Created the Base's metadata")

    async def cleanup():
        async with test_async_engine.begin() as conn:
            # Drop the schema after tests
            await conn.run_sync(Base.metadata.drop_all)
            print("***torn down the Base's metadata")

    # Use an event loop to ensure cleanup happens after tests complete
    request.addfinalizer(lambda: event_loop.run_until_complete(cleanup()))
    
    async with AsyncTestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture(scope="function")
async def redis_client__fixture(
    request,
    event_loop,
):
    # Initialize Redis client
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=3,  # Using db3 for property street test
    )

    async def cleanup():
        print("**closing redis")
        await redis_client.aclose()
        await redis_client.flushdb()

    # Use an event loop to ensure cleanup happens after tests complete
    request.addfinalizer(lambda: event_loop.run_until_complete(cleanup()))
    
    yield redis_client


@pytest.fixture(scope="function")
async def prod_redis_client__fixture(
    request,
    event_loop,
):
    # Initialize Redis client
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=REDIS_CACHE_DB,  # Using db3 for property street test
        decode_responses=True,
    )

    async def cleanup():
        print("**closing redis")
        await redis_client.aclose()

    # Use an event loop to ensure cleanup happens after tests complete
    request.addfinalizer(lambda: event_loop.run_until_complete(cleanup()))
    
    yield redis_client


@pytest.fixture(scope="function")
async def client__fixture(
    get_test_db__fixture, 
    redis_client__fixture,
    prod_redis_client__fixture
):
    # Pytest will handle awaiting the fixtures; don't manually await them
    test_db = await get_test_db__fixture.__anext__()
    redis_client_fixture = await redis_client__fixture.__anext__()
    prod_redis_client_fixture = await prod_redis_client__fixture.__anext__()

    # Override dependencies with callables
    async def override_get_db():
        yield test_db
    app.dependency_overrides[get_db] = override_get_db

    async def override_redis_client():
        yield redis_client_fixture
    app.dependency_overrides[redis_client] = override_redis_client

    async def override_prod_redis_client():
        yield prod_redis_client_fixture
    app.dependency_overrides[redis_client] = override_prod_redis_client

    # Use ASGITransport with the app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield {
            "http_client": ac, 
            "redis_client": redis_client_fixture,
            "db": test_db,
            "prod_redis_client": prod_redis_client_fixture
        }

