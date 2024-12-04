import pytest
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from property_street_backend.app.main import app

@pytest.mark.asyncio
async def test_db_connectivity(get_test_db__fixture: AsyncSession):
    try:

        test_db = await get_test_db__fixture

        assert isinstance(test_db, AsyncSession)
    finally:
        print("***closing connection")
        await test_db.close()


@pytest.mark.asyncio
async def test_client_connectivity(client__fixture):
    # fetch the client generator
    client_gen =  client__fixture
    # get the yield client objects
    client, redis_client = await client_gen.__anext__()

    assert isinstance(redis_client, redis.Redis)

    # Making a request to a URL
    url = "/"
    response = await client.get(url)

    # Checking the response
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}

    # Making a request to a URL
    url = "/test-redis"
    response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"test_key": "value"}



@pytest.mark.asyncio
async def test_redis_connectivity(redis_client__fixture):
    # fetch the client fixture
    redis_client =  await redis_client__fixture

    # Making a request to a URL
    assert isinstance(redis_client, redis.Redis)


# Adding a pseudo endpoint to the FastAPI app for testing
@app.get("/pseudo-url")
async def pseudo_url():
    return {"message": "This is a pseudo endpoint"}