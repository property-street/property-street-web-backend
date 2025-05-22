from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine

from . import get_env
from property_street_backend.config.settings import DATABASE_URL, TEST_DATABASE_URL

Base = declarative_base()
_postgres_instances = {"engines": {}, "session_makers": {}, "active_connections": {}}


async def get_postgres_instance(**kwargs):
    env = get_env()
    env_is_test = env == "test"
    metadata_test_routine = kwargs.get("metadata_test_routine", True)
    skip_session_close = kwargs.get('skip_session_close',False)

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
                await conn.execute(text("DROP SCHEMA public CASCADE"))
                await conn.execute(text("CREATE SCHEMA public"))
                print("***Dropped and recreated public schema")
                await conn.run_sync(Base.metadata.create_all)
                print("***Created a new Base metadata")


    # Increment connection count
    _postgres_instances["active_connections"][key] = (
        _postgres_instances["active_connections"].get(key, 0) + 1
    )

    session: AsyncSession = _postgres_instances["session_makers"][key]()
    try:
        yield session
    finally:
        # Leave the session open if skip_session_close is True and the environment is 'test'
        skip_close = skip_session_close and env_is_test
        if not skip_close:
            await session.close()

        _postgres_instances["active_connections"][key] -= 1

        # Cleanup if no more connections
        if _postgres_instances["active_connections"][key] == 0:
            engine: AsyncEngine = _postgres_instances["engines"].pop(key, None)
            _postgres_instances["session_makers"].pop(key, None)
            _postgres_instances["active_connections"].pop(key, None)

            if engine:
                await engine.dispose()
