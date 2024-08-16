import pytest
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
    # get the yield client object
    client = await client_gen.__anext__()

    # Making a request to a URL
    url = "/"
    response = await client.get(url)

    # Checking the response
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}


# Adding a pseudo endpoint to the FastAPI app for testing
@app.get("/pseudo-url")
async def pseudo_url():
    return {"message": "This is a pseudo endpoint"}