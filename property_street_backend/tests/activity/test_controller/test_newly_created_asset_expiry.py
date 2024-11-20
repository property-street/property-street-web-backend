import asyncio
import pytest

@pytest.mark.asyncio
async def test_newly_created_asset_expiry(client__fixture: tuple):
    # Fetch the client generator
    client_gen = client__fixture
    # Get the yield client objects
    client, redis_client = await client_gen.__anext__()

    # Making a request to a URL to initiate the registration of the event
    url = "/"
    response = await client.get(url)

    # Checking the response
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}

    # Fabricate test data
    fabricated_asset_id = "12345"
    fabricated_detail = '{"title": "Test Asset", "description": "Temporary description"}'
    set_key = "newly_created_asset"
    hset_key = f"newly_created_asset:{fabricated_asset_id}"

    # Add the asset ID to the set
    await redis_client.sadd(set_key, fabricated_asset_id)

    # Add the string detail to the hset and set an expiry
    await redis_client.hset(hset_key, "newly_created_asset", fabricated_detail)
    await redis_client.expire(hset_key, 2)  # 2-second expiry

    # Sleep to ensure the expiry is triggered
    await asyncio.sleep(3)

    # Assert that the hset does not exist (expired)
    hset_exists = await redis_client.exists(hset_key)
    assert hset_exists == 0, "HSET key should have expired but still exists."

    # Assert that the asset ID has been removed from the set
    asset_in_set = await redis_client.sismember(set_key, fabricated_asset_id)
    assert asset_in_set == 0, "Asset ID should have been removed from the set but still exists."
