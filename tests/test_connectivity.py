import os
import time
import json
import pytest
import websockets
from redis.asyncio import Redis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.main import app
from .auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.auth import fetched_access_token

@pytest.mark.asyncio
async def test_db_connectivity(
    get_test_db__fixture
):
    # fetch the testdb
    async for test_db in get_test_db__fixture:
        break
    
    assert isinstance(test_db, AsyncSession)

@pytest.mark.asyncio
async def test_redis_connectivity(redis_client__fixture):
    
    # fetch the client fixture
    async for redis_client in redis_client__fixture:
        break

    # assertions
    assert redis_client.connection_pool.connection_kwargs['db'] == 1
    assert isinstance(redis_client, Redis)


@pytest.mark.asyncio
async def test_client_connectivity(client__fixture):
    
    # get the yield client objects
    async for fixture_obj in client__fixture:
        redis_client = fixture_obj.get("redis_client")
        http_client = fixture_obj.get("http_client")
        test_db = fixture_obj.get("db")
        break

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
async def test_websocket_client(app_subprocess, websocket_client_fixture):
    # get the yield client objects
    async for fixture_obj in websocket_client_fixture:
        test_db: AsyncSession = fixture_obj.get('db')
        redis_client: Redis = fixture_obj.get('redis_client')
        break

    test_user = await create_test_user(test_db)
    token_obj = fetched_access_token(test_user)
    token = token_obj['access_token']
    headers = {
        'Authorization' : f"Bearer {token}"
    }
    timestamp = int(time.time())
    uri = f'ws://localhost:8001/ws/{test_user.id}?last_n_timestamp={timestamp}&sesion_ts={timestamp}&test_ping=true'

    async with websockets.connect(
        uri,
        extra_headers = headers
    ) as websocket:
        await websocket.send(json.dumps({"type": "ping"}))
        response = json.loads(await websocket.recv())
        assert response["type"] == "pong"
        assert response["token"] == token
        assert response["username"] == test_user.username
        assert int(response["last_n_timestamp"]) == timestamp

    # test redis_client publishing and channel listener callback
    await redis_client.publish(f'test_channel_{test_user.id}',json.dumps({'greetings': 'hi'}))
    

# Adding a pseudo endpoint to the FastAPI app for testing
@app.get("/pseudo-url")
async def pseudo_url():
    return {"message": "This is a pseudo endpoint"}