import os
import pytest
import websockets
import redis.asyncio as redis
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.main import app
from .auth.test_user_creation import create_test_user

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
    assert isinstance(redis_client, redis.Redis)


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
    assert isinstance(redis_client, redis.Redis)
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
async def test_websocket_client(client__fixture):
    client = TestClient(app)
    # get the yield client objects
    async for fixture_obj in client__fixture:
        http_client = fixture_obj.get("http_client")
        test_db = fixture_obj.get("db")
        break

    token = "Bearer testtoken123"
    test_user = await create_test_user(test_db)
    # uri = f"ws://testserver:8001/ws/{test_user.id}?last_n_timestamp=1516790"

    with client.websocket_connect(
        f'/ws/{test_user.id}?last_n_timestamp=1516790',
        headers={"Authorization": token}
    ) as websocket:
        websocket.send_json({"type": "ping"})
        response = websocket.receive_json()
        assert response["type"] == "pong"

# Adding a pseudo endpoint to the FastAPI app for testing
@app.get("/pseudo-url")
async def pseudo_url():
    return {"message": "This is a pseudo endpoint"}