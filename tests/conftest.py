import os
import time
import pytest
import signal
import pytest
import asyncio
import requests
import platform
import subprocess
from httpx import AsyncClient, ASGITransport


from property_street_backend.app.main import app
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.config.context_sessions import get_db_based_on_context
from property_street_backend.app.controllers.cache_expiration import cache_expiry_initializer


@pytest.fixture
def test_env_var():
    os.environ["TEST_ENV"] = "true"
    yield
    os.environ.pop("TEST_ENV", None)


@pytest.fixture(scope="function")
async def get_test_db__fixture(test_env_var):
    async for session in get_db():
        yield session


@pytest.fixture(scope="function")
async def redis_client__fixture(test_env_var):
    # await redis_client.flushdb()
    async for redis_client in get_redis():
        yield redis_client


@pytest.fixture(scope="function")
async def client__fixture(
    get_test_db__fixture, 
    redis_client__fixture,
):
    async for test_db in get_test_db__fixture:
        break

    async for test_redis_client in redis_client__fixture:
        break

    # overriding the client's get_db dependency
    app.dependency_overrides[get_db] = lambda: test_db  # Override get_db to use the test session
    app.dependency_overrides[get_redis] = lambda: test_redis_client  # Override redis_client dependency

    # Use ASGITransport with the app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield {
            "http_client": ac, 
            "redis_client": test_redis_client,
            "db": test_db,
        }


@pytest.fixture(scope='function')
async def sessions_fixture(get_test_db__fixture, redis_client__fixture):
    async for test_db in get_test_db__fixture:
        break
    async for test_redis_client in redis_client__fixture:
        break

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_redis] = lambda: test_redis_client

    yield {
        "redis_client": test_redis_client,
        "db": test_db,
    }

@pytest.fixture(scope='function')
async def sessions_with_cache_expiry_event_fixture(
    request, 
    event_loop,
    get_test_db__fixture, 
    redis_client__fixture, 
):
    async for test_db in get_test_db__fixture:
        break
    async for test_redis_client in redis_client__fixture:
        break

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_redis] = lambda: test_redis_client

    # ✅ FIXED: Properly await the initializer
    (
        listener_task, 
        stop_event, 
        _
    ) = await cache_expiry_initializer(test_redis_client)
    
    # ✅ Finalizer for cleanup
    async def finalizer():
        if stop_event:
            stop_event.set()
        if listener_task:
            await listener_task

    # ✅ Register the async finalizer using pytest
    request.addfinalizer(lambda: event_loop.run_until_complete(finalizer()))

    
    yield {
        "redis_client": test_redis_client,
        "db": test_db,
    }


@pytest.fixture(scope="function")
def celery_worker_and_beat():
    env = os.environ.copy()
    env["TEST_ENV"] = "True"

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


@pytest.fixture(scope="function")
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