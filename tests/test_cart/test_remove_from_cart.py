import json
import pytest

from .test_objects import test_cart_object
from property_street_backend.app.controllers.cart.cart_methods import CartService
from property_street_backend.app.controllers.cart.models import CartItem
from property_street_backend.tests.activity.test_controller.test_asset_creation import create_test_agent, create_test_asset


@pytest.mark.asyncio
async def test_remove_from_cart(client__fixture):
    test_user_id = 1
    cart_key = f"cart_{test_user_id}"
    cart_pre_offload_key = f"cart_pre_offload_{test_user_id}"
    cart_pre_deletion_key = f"cart_pre_deletion_{test_user_id}"
    cart_object_keys = list(test_cart_object.keys())
    cart_ttl = 2

    # get the yield client objects
    fixture_obj = await client__fixture.__anext__()
    # extract the database entry
    redis_client = fixture_obj.get("redis_client")

    # add multiple (2) cart item to the pre_offload set
    # call the remove_from_cart with one asset_id
    # assert that the cart-item deleted no longer exists
    await redis_client.set(cart_pre_offload_key, json.dumps(test_cart_object))
    asset_id = cart_object_keys[0]
    await CartService.remove_from_cart(
        user_id = test_user_id,
        asset_id = asset_id,
        cart_ttl = cart_ttl,
        redis_client= redis_client
    )
    cart_pre_offload_data = await redis_client.get(cart_pre_offload_key)
    loaded_cart_pre_offload_data = json.loads(cart_pre_offload_data)
    assert not loaded_cart_pre_offload_data.get(f'{asset_id}')
    # call the remove_from_cart again with the test_object's second asset_id
    # assert that the pre_offload set no longer exists
    asset_id2 = cart_object_keys[1]
    await CartService.remove_from_cart(
        user_id = test_user_id,
        asset_id = asset_id2,
        cart_ttl = cart_ttl,
        redis_client= redis_client
    )
    assert not await redis_client.exists(cart_pre_offload_key)

    # add multiple (2) cart item to the cart set
    # call the remove_from_cart with one asset_id
    # assert that the cart-item deleted no longer exists in the cart set 
    # check that it exists in the pre_deletion set
    await redis_client.set(cart_key, json.dumps(test_cart_object))
    asset_id = cart_object_keys[0]
    await CartService.remove_from_cart(
        user_id = test_user_id,
        asset_id = asset_id,
        cart_ttl = cart_ttl,
        redis_client= redis_client
    )
    cart_data = await redis_client.get(cart_key)
    loaded_cart_data = json.loads(cart_data)
    assert not loaded_cart_data.get(f'{asset_id}')
    cart_pre_deletion_data = await redis_client.get(cart_pre_deletion_key)
    loaded_cart_pre_deletion_data = json.loads(cart_pre_deletion_data)
    assert loaded_cart_pre_deletion_data[f'{asset_id}']['price'] == test_cart_object[asset_id]['price']
    # call the remove_from_cart again with another asset_id
    # assert that the cart set no longer exists
    # assert that the asset_deleted is present in the pre_deletion set
    asset_id = cart_object_keys[1]
    await CartService.remove_from_cart(
        user_id = test_user_id,
        asset_id = asset_id,
        cart_ttl = cart_ttl,
        redis_client= redis_client
    )
    assert not await redis_client.exists(cart_key)
    cart_pre_deletion_data = await redis_client.get(cart_pre_deletion_key)
    loaded_cart_pre_deletion_data = json.loads(cart_pre_deletion_data)
    assert loaded_cart_pre_deletion_data[f'{asset_id}']['price'] == test_cart_object[asset_id]['price']