import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport
from pystyle import Colors

from property_street_backend.app.database import Base, get_db
from property_street_backend.app.main import app
from property_street_backend.config.settings import TEST_DATABASE_URL

# Async SQLAlchemy engine and session for testing
# async_engine: An asynchronous SQLAlchemy engine created using create_async_engine for the test database.
# TestingSessionLocal: An asynchronous session factory created using sessionmaker with AsyncSession.

test_async_engine = create_async_engine(TEST_DATABASE_URL, echo=True)
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
async def get_test_db__fixture(request, event_loop):
    
    async with test_async_engine.begin() as conn:
        # Create the database schema
        print(Colors.green, "***Creating the Base's metadata")
        await conn.run_sync(Base.metadata.create_all)

    # Finalizer function
    async def cleanup_testdb():
        async with test_async_engine.begin() as conn:
            # Drop the schema after tests
            await conn.run_sync(Base.metadata.drop_all)
            print(Colors.green, "***tearing down the Base's metadata")

    # Use an event loop to ensure cleanup happens after tests complete
    request.addfinalizer(lambda: event_loop.run_until_complete(cleanup_testdb()))

    async with AsyncTestSessionLocal() as session:
        return session


@pytest.fixture(scope="function")
async def client__fixture(get_test_db__fixture, request, event_loop):
    # getting the test_db fixture
    test_db = await get_test_db__fixture
    # overriding the client's get_db dependency
    app.dependency_overrides[get_db] = lambda: test_db  # Override get_db to use the test session

    # cleanup to close the test database
    async def cleanup():
        await test_db.close()

    # Use an event loop to ensure cleanup happens after tests complete
    request.addfinalizer(lambda: event_loop.run_until_complete(cleanup()))
    
    # Use ASGITransport with the app
    transport = ASGITransport(app=app)
    # return the client instance
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


