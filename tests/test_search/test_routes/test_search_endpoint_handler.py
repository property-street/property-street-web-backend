import pytest, json, asyncio
import redis.asyncio as redis 
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.tests.activity.test_controller.test_asset_creation import (
    create_test_asset,
    create_test_agent,
)

zset_key = "trending_searches"

@pytest.mark.asyncio
async def test_search_endpoint_when_response_is_in_cache(
    client__fixture_with_prod_redis,
):
    # get fixtures
    client, redis_client = await client__fixture_with_prod_redis.__anext__()

    # get fixtures
    # fixture_obj = await client__fixture_with_prod_redis.__anext__()
    # redis_client = fixture_obj.get('redis_client')
    # client = fixture_obj.get('client')
    
    try:
        set_key = 'recent_1 bedroom'
        zset_entry = '1 bedroom'
        expiry_seconds = 2
        asset_data = {"name": "Test Asset", "category": "Test Category"}
        search_token_list = ["1 bedroom:none"]

        # create the test set
        # make the post request
        # assert that `1 bedroom is an entry in the zset`
        # make the function to sleep for expiry seconds + 1
        await redis_client.set(set_key, json.dumps(asset_data), ex=10)
        payload = {
            "entries": search_token_list,
            "ttl": expiry_seconds
        }
        response = await client.post(
            "/search",
            json=payload
        )
        assert response.status_code == 200
        assert response is not None
        score = await redis_client.zscore(zset_key, zset_entry)
        assert score == 1
        await asyncio.sleep(expiry_seconds+1)

        # check that the set no longer exists
        # assert that the entry is no longer a member of the zset
        assert not await redis_client.exists(set_key)
        is_member = await redis_client.zscore(zset_key, zset_entry)
        assert is_member is None
    finally: 
        # delete the set
        # delete the zset
        await redis_client.delete(set_key)
        await redis_client.delete(zset_key)


@pytest.mark.asyncio
async def test_search_endpoint_when_response_is_in_db(
    client__fixture_with_prod_redis,
):
    try:
        # get fixtures
        client, redis_client = await client__fixture_with_prod_redis.__anext__()

        set_key = 'recent_1 bedroom'
        zset_entry = '1 bedroom'
        expiry_seconds = 2
        asset_data = {"name": "Test Asset", "category": "Test Category"}
        search_token_list = ["1 bedroom:none"]

        # create the test set
        # make the post request
        # assert that `1 bedroom is an entry in the zset`
        # make the function to sleep for expiry seconds + 1
        await redis_client.set(set_key, json.dumps(asset_data), ex=10)
        payload = {
            "entries": search_token_list,
            "ttl": expiry_seconds
        }
        response = await client.post(
            "/search",
            json=payload
        )
        assert response.status_code == 200
        assert response is not None
        score = await redis_client.zscore(zset_key, zset_entry)
        assert score == 1
        await asyncio.sleep(expiry_seconds+1)

        # check that the set no longer exists
        # assert that the entry is no longer a member of the zset
        assert not await redis_client.exists(set_key)
        is_member = await redis_client.zscore(zset_key, zset_entry)
        assert is_member is None
    finally: 
        # delete the set
        # delete the zset
        await redis_client.delete(set_key)
        await redis_client.delete(zset_key)
