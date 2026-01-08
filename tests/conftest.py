import os
import time
import signal
import pytest
import asyncio
import requests
import platform
import subprocess
import pytest_asyncio
from sqlalchemy import text
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport


from property_street_backend.app.main import app
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis, logger
from property_street_backend.config.redis_connection_manager import get_redis_instance
from property_street_backend.app.controllers.cache_expiration import cache_expiry_initializer
from property_street_backend.app.controllers.cache_expiration.expiry_pubsub_listener import expiry_pubsub_loop_entered 
from property_street_backend.config.postgres_connection_manager import Base, runtime_async_session_maker, runtime_async_engine


load_dotenv()

@pytest_asyncio.fixture(scope="function")
def test_env_var():
    os.environ["TEST_ENV"] = "true"
    yield
    os.environ.pop("TEST_ENV", None)

@pytest_asyncio.fixture(scope="function")
def ignore_cloud_image_del():
    os.environ["TEST_CLOUD_IMAGE_DEL"] = "true"
    yield
    os.environ.pop("TEST_CLOUD_IMAGE_DEL", None)
    

@pytest_asyncio.fixture(scope="function")
async def get_test_db__fixture(test_env_var):
    # Create a clean database if it's a test environment
    async_engine = runtime_async_engine()
    async with async_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        logger.info("***Dropped and recreated public schema")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("***Created a new Base metadata")
    
    async_session_maker = runtime_async_session_maker()
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def redis_client__fixture(test_env_var):
    async with get_redis_instance() as redis_client:
        await redis_client.flushdb()
        yield redis_client


@pytest_asyncio.fixture(scope="function")
async def client__fixture(
    get_test_db__fixture, 
    redis_client__fixture,
):
    # overriding the client's get_db dependency
    app.dependency_overrides[get_db] = lambda: get_test_db__fixture  # Override get_db to use the test session
    app.dependency_overrides[get_redis] = lambda: redis_client__fixture  # Override redis_client dependency

    # Use ASGITransport with the app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield {
            "http_client": ac, 
            "redis_client": redis_client__fixture,
            "db": get_test_db__fixture,
        }


@pytest_asyncio.fixture(scope="function")
async def sessions_fixture(get_test_db__fixture, redis_client__fixture):
    app.dependency_overrides[get_db] = lambda: get_test_db__fixture
    app.dependency_overrides[get_redis] = lambda: redis_client__fixture

    yield {
        "redis_client": redis_client__fixture,
        "db": get_test_db__fixture,
    }


@pytest_asyncio.fixture(scope="function")
async def sessions_with_cache_expiry_event_fixture(
    request, 
    event_loop,
    get_test_db__fixture, 
    redis_client__fixture, 
):
    app.dependency_overrides[get_db] = lambda: get_test_db__fixture
    app.dependency_overrides[get_redis] = lambda: redis_client__fixture

    # ✅ FIXED: Properly await the initializer
    (
        listener_task, 
        stop_event, 
        _
    ) = await cache_expiry_initializer(redis_client__fixture)
    
    # ✅ Finalizer for cleanup
    async def finalizer():
        if stop_event:
            stop_event.set()
        if listener_task:
            await listener_task

    # ✅ Register the async finalizer using pytest
    request.addfinalizer(lambda: event_loop.run_until_complete(finalizer()))

    # ✅ Poll until the listener loop is confirmed to be active
    for _ in range(60):
        loop_entered = await redis_client__fixture.exists(expiry_pubsub_loop_entered)
        if loop_entered:
            break
        await asyncio.sleep(0.1)  # prevent tight loop

    if not loop_entered:
        raise Exception("Expiry pubsub listener never started.")
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield {
            "http_client": ac, 
            "redis_client": redis_client__fixture,
            "db": get_test_db__fixture,
        }


@pytest_asyncio.fixture(scope="function")
def celery_worker_and_beat(test_env_var):
    env = os.environ.copy()
    #  env["TEST_ENV"] = "True"

    is_windows = platform.system() == "Windows"

    if is_windows:
        # On Windows, use creationflags to create a new process group
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        worker = subprocess.Popen(
            [
                "celery", "-A", "property_street_backend.app.celery_config", "worker",
                "--pool=solo", "--loglevel=info", "-E"
            ],
            env=env,
            creationflags=creationflags
        )
        beat = subprocess.Popen(
            [
                "celery", "-A", "property_street_backend.app.celery_config", "beat",
                "--loglevel=info"
            ],
            env=env,
            creationflags=creationflags
        )
    else:
        # On Unix, use preexec_fn to set new process group
        worker = subprocess.Popen(
            [
                "celery", "-A", "property_street_backend.app.celery_config", "worker",
                "--pool=solo", "--loglevel=info", "-E"
            ],
            env=env,
            preexec_fn=os.setsid
        )
        beat = subprocess.Popen(
            [
                "celery", "-A", "property_street_backend.app.celery_config", "beat",
                "--loglevel=info"
            ],
            env=env,
            preexec_fn=os.setsid
        )

    # Give them time to start
    time.sleep(5)

    yield

    # Graceful shutdown
    if is_windows:
        worker.send_signal(signal.CTRL_BREAK_EVENT)
        beat.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        os.killpg(os.getpgid(worker.pid), signal.SIGTERM)
        os.killpg(os.getpgid(beat.pid), signal.SIGTERM)

    worker.wait()
    beat.wait()


@pytest_asyncio.fixture(scope="function")
def app_subprocess(test_env_var):
    # On Windows, use creationflags to create a new process group
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    app = subprocess.Popen(
        [
            "uvicorn", "app.main:app", "--port",
            "8001",
        ],
        creationflags=creationflags
    )

    # Give time to start
    for _ in range(20):
        try:
            requests.get(f'http://localhost:8001/?session={int(time.time())}')
            break
        except Exception:
            time.sleep(1)  # ←
    
    yield

    # Graceful shutdown
    app.send_signal(signal.CTRL_BREAK_EVENT)

    app.wait()