import os
import time
import pytest
import signal
import pytest
import platform
import subprocess
import redis.asyncio as redis
from httpx import AsyncClient, ASGITransport

from property_street_backend.app.main import app
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.config.settings import (
    PROD_REDIS_CACHE_DB,
)
from property_street_backend.config.redis_connection_manager import (
    get_redis_instance,
)
from property_street_backend.config.postgres_connection_manager import get_postgres_instance

def test_with_monkeypatch(monkeypatch):
    monkeypatch.setenv("MY_ENV_VAR", "from_monkey")
    
@pytest.fixture
def set_env_var():
    def _set(key, value):
        os.environ[key] = value
        yield
        os.environ.pop(key, None)
    return _set

async def get_test_db(**kwargs):
    env = 'test'
    async for test_db in get_postgres_instance(env,**kwargs):
        yield test_db


async def get_test_redis():
    env = "test"
    async for redis_client in get_redis_instance(env):
        yield redis_client


@pytest.fixture(scope="function")
async def get_test_db__fixture():
        
    async for session in get_test_db():
        yield session

    # Use an event loop to ensure cleanup happens after tests complete
    # request.addfinalizer(lambda: event_loop.run_until_complete(cleanup_testdb()))



@pytest.fixture(scope="function")
async def redis_client__fixture():
    # Initialize Redis client
    async for redis_client in get_test_redis():
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
        db=PROD_REDIS_CACHE_DB,  # Using db3 for property street test
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
):
    # getting the test_db fixture
    async for test_db in get_test_db__fixture:
        break

    # get the yield client object
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


@pytest.fixture(scope="function")
async def client__fixture_with_prod_redis(
    request,
    event_loop,
    get_test_db__fixture, 
    prod_redis_client__fixture,
):
    # getting the test_db fixture
    test_db = await get_test_db__fixture

    # get the yield client object
    prod_redis_client = await prod_redis_client__fixture.__anext__()

    # overriding the client's get_db dependency
    app.dependency_overrides[get_db] = lambda: test_db  # Override get_db to use the test session
    app.dependency_overrides[get_redis] = lambda: prod_redis_client  # Override redis_client dependency

    # cleanup to close the test database
    async def cleanup():
        await test_db.close()

    # Use an event loop to ensure cleanup happens after tests complete
    request.addfinalizer(lambda: event_loop.run_until_complete(cleanup()))
    

    # Use ASGITransport with the app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield {
            "http_client": ac, 
            "redis_client": prod_redis_client,
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