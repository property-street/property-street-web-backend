import json
import pytest
import asyncio
from sqlalchemy.future import select

from .test_objects import test_cart_object
from property_street_backend.app.controllers.cart.models import CartItem
from property_street_backend.config.settings import TEST_CART_OFFLOAD_SCHEDULE, TEST_CART_TTL

@pytest.mark.asyncio
async def test_cart_offload(client__fixture):
    """Tests celery offload

    Args:
        client__fixture (_type_): async generator object that contains test dependencies
    """
    test_user_id = 1
    cart_key = f"cart_{test_user_id}"
    cart_pre_offload_key = f"cart_pre_offload_{test_user_id}"
    cart_object_keys = list(test_cart_object.keys())
    asset_id1 = cart_object_keys[0]
    asset_id2 = cart_object_keys[1]

    # turn on the celery worker and scheduler
    # Extract the fixture object
    async for fixture_obj in client__fixture:
        test_db = fixture_obj.get("db")
        redis_client = fixture_obj.get("redis_client")
        break  # Stop iteration after first fixture retrieval

    # add items to the pre_offload set
    # wait for offload seconds
    await redis_client.set(cart_pre_offload_key, json.dumps(test_cart_object))
    await asyncio.sleep(TEST_CART_OFFLOAD_SCHEDULE+1)
    # check that those items are in the cart set
    # wait for ttl seconds to confirm expiration
    cart_data = json.loads(await redis_client.get(cart_key))
    assert cart_data[f'{asset_id1}']['price'] == test_cart_object[asset_id1]['price']
    assert cart_data[f'{asset_id2}']['price'] == test_cart_object[asset_id2]['price']
    # await asyncio.sleep(TEST_CART_TTL+1)
    # assert not await redis_client.get(cart_key)
    # confirm that data persists in the database
    # query = await test_db.execute(
    #     select(CartItem).filter(CartItem.user_id == test_user_id)
    # )
    # result = query.scalars().all()
    # assert len(result) == 2