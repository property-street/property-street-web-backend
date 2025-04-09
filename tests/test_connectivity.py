import pytest
import asyncio
import redis.asyncio as redis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from property_street_backend.app.main import app

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
async def test_prod_redis_connectivity(prod_redis_client__fixture):
    # retrieve the redis instance
    redis_client =  await prod_redis_client__fixture.__anext__()

    # assertions
    assert int(redis_client.connection_pool.connection_kwargs['db']) == 0
    assert isinstance(redis_client, redis.Redis)


# Adding a pseudo endpoint to the FastAPI app for testing
@app.get("/pseudo-url")
async def pseudo_url():
    return {"message": "This is a pseudo endpoint"}