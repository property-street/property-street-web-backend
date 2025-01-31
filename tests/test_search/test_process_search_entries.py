import pytest, json, asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from property_street_backend.app.controllers.search.search_string_processor import (
    process_search_entries
)

zset_key = "trending_searches"

@pytest.mark.asyncio
async def test_process_search_entries_when_response_is_in_cache(
    client__fixture
):
    try:
        # Connect to the Redis server
        fixture_obj = await client__fixture.__anext__()
        prod_redis_client = fixture_obj.get("prod_redis_client")
        test_db = fixture_obj.get("db")

        set_key = 'recent_1 bedroom'
        zset_entry = '1 bedroom'
        expiry_seconds = 2
        asset_data = {"name": "Test Asset", "category": "Test Category"}
        search_token_list = ["1 bedroom:none"]

        # create the test set
        # call the process search function
        # assert that `1 bedroom is an entry in the zset`
        # make the function to sleep for expiry seconds + 1
        await prod_redis_client.set(set_key, json.dumps([asset_data,]), ex=10)
        result = await process_search_entries(
            entries= search_token_list,
            redis_client= prod_redis_client,
            db_session = test_db,
            expiry_seconds = expiry_seconds
        )
        assert isinstance(result, list)
        assert result[0] == asset_data
        score = await prod_redis_client.zscore(zset_key, zset_entry)
        assert score == 1
        await asyncio.sleep(expiry_seconds+1)

        # check that the set no longer exists
        # assert that the entry is no longer a member of the zset
        assert not await prod_redis_client.exists(set_key)
        is_member = await prod_redis_client.zscore(zset_key, zset_entry)
        assert is_member is None
    finally: 
        # delete the set
        # delete the zset
        await prod_redis_client.delete(set_key)
        await prod_redis_client.delete(zset_key)


