from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from property_street_backend.config.settings import DATABASE_URL, TEST_DATABASE_URL

Base = declarative_base()
_postgres_instances = {"engines": {}, "session_makers": {}, "active_connections": {}}

async def get_postgres_instance(env: str = None, **kwargs):
    env_is_test = env == "test"
    metadata_test_routine = kwargs.get("metadata_test_routine", True)

    database_url = TEST_DATABASE_URL if env_is_test else DATABASE_URL
    key = f"{env}_{database_url}"

    if key not in _postgres_instances["engines"]:
        # Create and store engine and session maker
        async_engine = create_async_engine(database_url, echo=False)
        SessionLocal = sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )

        _postgres_instances["engines"][key] = async_engine
        _postgres_instances["session_makers"][key] = SessionLocal

        if env_is_test and metadata_test_routine:
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                print("***Torn down the previous Base's metadata")
                await conn.run_sync(Base.metadata.create_all)
                print("***Created the Base's metadata")

    # Increment connection count
    _postgres_instances["active_connections"][key] = (
        _postgres_instances["active_connections"].get(key, 0) + 1
    )

    session = _postgres_instances["session_makers"][key]()
    try:
        yield session
    finally:
        await session.close()

        _postgres_instances["active_connections"][key] -= 1

        # Cleanup if no more connections
        if _postgres_instances["active_connections"][key] == 0:
            engine = _postgres_instances["engines"].pop(key, None)
            _postgres_instances["session_makers"].pop(key, None)
            _postgres_instances["active_connections"].pop(key, None)

            if engine:
                await engine.dispose()
