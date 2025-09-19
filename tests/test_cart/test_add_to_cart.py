import json
import pytest
import asyncio

from .test_objects import test_cart_object
from property_street_backend.app.controllers.cart.cart_methods import CartService

@pytest.mark.asyncio
async def test_add_to_cart(client__fixture):
    """Tests the add_cart functionality of the custom cart package

    Args:
        client__fixture (_type_): Generator function that returns fixture objects
    """
    # get the yield client objects
    fixture_obj = await client__fixture.__anext__()
    # extract the database entry
    redis_client = fixture_obj.get("redis_client")

    cart_ttl = 2
    test_user_id = 1
    test_asset_id = list(test_cart_object.keys())[0]
    test_cart_item_details = test_cart_object[test_asset_id]
    cart_key = f'cart_{test_user_id}'
    cart_pre_offload_key = f'cart_pre_offload_{test_user_id}'
    cart_pre_deletion_key = f'cart_pre_deletion_{test_user_id}'


    #**# test when data is in pre_deletion_cart
    # add items to the pre_deletion_cart cache and retrieve the item
    # call the add_to_cart method
    # confirm deletion of the pre_deletion cart
    # get the same item from the cart set
    # confirm addition of items to the cart cache
    await redis_client.set(cart_pre_deletion_key, json.dumps({test_asset_id:test_cart_object[test_asset_id]}))
    await CartService.add_to_cart(
        user_id = test_user_id,
        asset_id = test_asset_id,
        cart_ttl = cart_ttl,
        redis_client = redis_client,
        cart_item_details=test_cart_item_details
    )
    assert not await redis_client.exists(cart_pre_deletion_key)
    cart_item = await redis_client.get(cart_key)
    loaded_cart_item = json.loads(cart_item)
    assert loaded_cart_item[f'{test_asset_id}']['asset_cover_url'] == test_cart_object[test_asset_id]['asset_cover_url']
    

    #**# test when a new data is added
    # call the add_to_cart method
    # confirm it's addition
    # assert that after cart_ttl + 1 secs, the cart wont exists
    test_asset_id2 = list(test_cart_object.keys())[1]
    test_cart_item_details2 = test_cart_object[test_asset_id2]
    await CartService.add_to_cart(
        user_id = test_user_id,
        asset_id = test_asset_id2,
        cart_ttl = cart_ttl,
        redis_client = redis_client,
        cart_item_details=test_cart_item_details2
    )
    cart_item = await redis_client.get(cart_key)
    loaded_cart_item = json.loads(cart_item)
    assert loaded_cart_item[f'{test_asset_id2}']['price'] == test_cart_object[test_asset_id2]['price']
    await asyncio.sleep(cart_ttl+1)
    assert not await redis_client.exists(cart_key)

    
    #**# test when no cache data exists
    # delete items of the cart set from previous case
    # call the add_to_cart with the data
    # confirm addition of items to the cart_pre_offload cache
    await redis_client.delete(cart_key)
    await CartService.add_to_cart(
        user_id = test_user_id,
        asset_id = test_asset_id,
        cart_ttl = cart_ttl,
        redis_client = redis_client,
        cart_item_details=test_cart_item_details
    )
    cart_pre_offload_item = await redis_client.get(cart_pre_offload_key)
    loaded_cart_pre_offload_item = json.loads(cart_pre_offload_item)
    assert loaded_cart_pre_offload_item[f'{test_asset_id}']['price'] == test_cart_object[test_asset_id]['price']