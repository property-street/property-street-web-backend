import json
import pytest
import asyncio

from .test_objects import test_cart_object
from property_street_backend.app.controllers.cart.cart_methods import CartService
from property_street_backend.app.controllers.cart.models import CartItem
from property_street_backend.tests.activity.test_controller.test_asset_creation import create_test_agent, create_test_asset


@pytest.mark.asyncio
async def test_get_cart(client__fixture):
    """Tests the get_cart functionality of the custom cart package

    Args:
        client__fixture (_type_): Generator function that returns fixture objects
    """
    # test after adding items to a user's cart_pre_offload set
    # test after addting items to a user's cart
    # test after adding items to both user's cart_pre_offload and cart sets
    
    # get the yield client objects
    fixture_obj = await client__fixture.__anext__()
    # extract the database entry
    redis_client = fixture_obj.get("redis_client")
    test_db = fixture_obj.get("db")
    
    test_user_id = 1
    cart_key = f"cart_{test_user_id}"
    cart_pre_offload_key = f"cart_pre_offload_{test_user_id}"
    
    #**# Test only when data is cart_pre_offload object
    # set a cart_pre_offload_object
    # call the get cart method and make assertions
    await redis_client.set(cart_pre_offload_key, json.dumps(test_cart_object))
    cart_result = await CartService.get_cart(
        user_id = test_user_id,
        cart_ttl = 0, 
        db = test_db,
        redis_client = redis_client
    )
    assert len(cart_result.keys()) == 2
    assert cart_result.get('0')['quantity'] == test_cart_object[0]['quantity']
    assert cart_result.get('1')['price'] == test_cart_object[1]['price']


    #**# Test only when data is in cart
    # delete off cart_pre_offload items
    # add data to cart and make assertions
    await redis_client.delete(cart_pre_offload_key)
    await redis_client.set(cart_key, json.dumps(test_cart_object))
    cart_result = await CartService.get_cart(
        user_id = test_user_id,
        cart_ttl = 0, 
        db = test_db,
        redis_client = redis_client
    )
    assert len(cart_result.keys()) == 2
    assert cart_result.get('0')['quantity'] == test_cart_object[0]['quantity']
    assert cart_result.get('1')['price'] == test_cart_object[1]['price']


    #**# Test retrieval when no item is in the cache, but in the database
    # delete off the user cart=item
    # create a test agent 
    # create a test asset 
    # create a test cart-item with the agent's user profile
    await redis_client.delete(cart_key)
    test_agent = await create_test_agent(test_db)
    test_asset = await create_test_asset(test_db, test_agent.id)
    asset_id = test_asset.id
    test_cart_item = CartItem(
        asset_id = asset_id,
        user_id = test_agent.user.id,
    )
    test_db.add(test_cart_item)
    await test_db.commit()

    # call the get_cart method for the user
    # make assertions
    cart_ttl = 2 # 2 seconds
    cart_result = await CartService.get_cart(
        user_id = test_agent.user.id,
        cart_ttl = cart_ttl,
        db = test_db,
        redis_client = redis_client,  
    )
    await test_db.refresh(test_cart_item)
    assert len(cart_result) == 1
    assert cart_result[asset_id]['quantity'] == test_cart_item.quantity
    assert cart_result[asset_id]['asset_cover_url'] == test_cart_item.asset.cover_image.secure_url
    assert cart_result[asset_id]['asset_title'] == test_cart_item.asset.title
    assert cart_result[asset_id]['price'] == test_cart_item.asset.price

    # test the expiry of the client's cart set
    await asyncio.sleep(cart_ttl+1)
    assert not await redis_client.exists(cart_key)
