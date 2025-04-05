import json
import pytest

from .test_objects import test_cart_object
from property_street_backend.app.controllers.cart.cart_methods import CartService


@pytest.mark.asyncio
async def test_clear_cart(client__fixture):
    # get the yield client objects
    fixture_obj = await client__fixture.__anext__()
    # extract the database entry
    redis_client = fixture_obj.get("redis_client")

    test_user_id = 1
    cart_key = f"cart_{test_user_id}"
    cart_pre_offload_key = f"cart_pre_offload_{test_user_id}"
    cart_pre_deletion_key = f"cart_pre_deletion_{test_user_id}"
    cart_object_keys = list(test_cart_object.keys())

    # add different data to the cart and cart_pre_offload set
    # call the clear_cart method
    # assert that the data are all present in the pre_deletion set
    # assert those carts have been deleted
    asset_id1 = cart_object_keys[0]
    asset_id2 = cart_object_keys[1]
    await redis_client.set(cart_pre_offload_key, json.dumps({asset_id1:test_cart_object[asset_id1]}))
    await redis_client.set(cart_key, json.dumps({asset_id2:test_cart_object[asset_id2]}))
    await CartService.clear_cart(
        user_id = test_user_id,
        redis_client = redis_client
    )
    cart_pre_deletion_data = json.loads(await redis_client.get(cart_pre_deletion_key))
    assert cart_pre_deletion_data[f'{asset_id1}']['price'] == test_cart_object[asset_id1]['price']
    assert cart_pre_deletion_data[f'{asset_id2}']['price'] == test_cart_object[asset_id2]['price']
    assert not await redis_client.exists(cart_key)
    assert not await redis_client.exists(cart_pre_offload_key)