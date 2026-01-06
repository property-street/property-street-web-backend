import os
import time
import json
import pytest
import asyncio
import websockets
from sqlalchemy import select
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import create_test_user
from property_street_backend.app.main import app
from property_street_backend.app.models import User
from property_street_backend.config import env_is_test
from property_street_backend.config.settings import TEST_REDIS_CACHE_DB
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.config.postgres_connection_manager import get_postgres_instance


@pytest.mark.asyncio
async def test_get_env_a(test_env_var):
    assert env_is_test()

@pytest.mark.asyncio
async def test_get_env_b():
    assert not env_is_test()


@pytest.mark.asyncio
async def test_db_connectivity(get_test_db__fixture):
    # fetch the testdb
    test_db = get_test_db__fixture
    assert isinstance(test_db, AsyncSession)


@pytest.mark.asyncio
async def test_db_persistence_multi_session(
    get_test_db__fixture
):
    test_db = get_test_db__fixture
    assert isinstance(test_db, AsyncSession)
    test_user: User = await create_test_user(test_db)
    
    async with get_postgres_instance() as test_db2:
        test_db2: AsyncSession
        stmt = await test_db2.execute(
            select(User).filter(User.email == test_user.email)
        )
        result = stmt.scalars().first()
        assert result


@pytest.mark.asyncio
async def test_redis_connectivity(redis_client__fixture):
    redis_client: Redis = redis_client__fixture
    assert redis_client.connection_pool.connection_kwargs['db'] == TEST_REDIS_CACHE_DB
    assert isinstance(redis_client, Redis)


@pytest.mark.asyncio
async def test_client_connectivity(client__fixture):
    
    # get the yield client objects
    fixture_obj: dict = client__fixture
    redis_client: Redis = fixture_obj.get("redis_client")
    http_client: AsyncClient = fixture_obj.get("http_client")
    test_db: AsyncSession = fixture_obj.get("db")

    # environment varible assertion
    assert os.getenv("TEST_ENV") == "true"

    # database assertion
    assert isinstance(test_db, AsyncSession)

    # make assertions for the test redis_client
    assert isinstance(redis_client, Redis)
    assert redis_client.connection_pool.connection_kwargs['db'] == 1
    
    # assertions for client
    assert isinstance(http_client, AsyncClient)
    
    # Making a request to a URL
    # asserting response
    url = "/"
    response = await http_client.get(url)
    assert response.status_code == 200
    assert response.json() == {
        "message": "Hello, World!",
        "environment": "development"
    }

    # Making a request to a URL
    # making assertions
    url = "/test-database"
    response = await http_client.get(url)
    assert response.status_code == 200
    assert response.json().get("database_connected")

    # Making a request to a URL
    # making assertions
    url = "/test-redis"
    response = await http_client.get(url)
    assert response.status_code == 200
    assert response.json().get("test_key") == "value"


@pytest.mark.asyncio
async def test_websocket_client(app_subprocess, get_test_db__fixture):
    # get the yield client objects
    test_db : AsyncSession = get_test_db__fixture

    test_user = await create_test_user(test_db)
    await test_user.become_agent(test_db)

    token_obj = fetch_access_token(test_user)
    token = token_obj['access_token']
    timestamp = int(time.time())
    uri = f'ws://localhost:8001/ws?last_n_timestamp={timestamp}&sesion_ts={timestamp}&test_ping=true&access_token={token}'
    test_ws = await websockets.connect(uri)
    
    try:
        response = json.loads( 
            await asyncio.wait_for( test_ws.recv(), timeout = 60 )
        )
        assert response["token"] == token
        assert response["username"] == test_user.username
        assert int(response["last_n_timestamp"]) == timestamp
        assert response["is_agent"]
    finally:
        if test_db:
            await test_db.close()
        if test_ws:
            await test_ws.close()

# Adding a pseudo endpoint to the FastAPI app for testing
@app.get("/pseudo-url")
async def pseudo_url():
    return {"message": "This is a pseudo endpoint"}