import json
import pytest
import asyncio
from sqlalchemy.future import select

from .test_objects import test_cart_object
from property_street_backend.app.controllers.auth import create_agent
from property_street_backend.app.controllers.cart.models import CartItem
from property_street_backend.app.models import Asset
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.config.settings import TEST_CART_OFFLOAD_SCHEDULE, TEST_CART_TTL
from property_street_backend.app.controllers.cart.routines.offload_task import handle_cart_offload

@pytest.mark.asyncio
async def test_cart_offload(client__fixture,celery_worker_and_beat):
    """Tests that cart offload moves items from pre_offload to cart and persists in DB

    Args:
        client__fixture (_type_): async generator object that contains test dependencies
    """
    # turn on the celery worker and scheduler
    # Extract the fixture object
    async for fixture_obj in client__fixture:
        test_db = fixture_obj.get("db")
        redis_client = fixture_obj.get("redis_client")
        break  # Stop iteration after first fixture retrieval

    # Define a test user
    # Call the create_user function
    user_data = UserRegistrationSchema(
        email="test@example.com",
        username="testuser",
        password="password123"
    )
    created_agent = await create_agent(test_db, user_data)
    test_user_id = created_agent.user.id

    # cart utility keys
    cart_key = f"cart_{test_user_id}"
    cart_pre_offload_key = f"cart_pre_offload_{test_user_id}"

    # Create test assets
    # modify the test_cart_object
    asset1 = Asset(
        agent_id=created_agent.id,
        title="Test Asset 1",
        category="Real Estate",
        country="USA",
        address="123 Main St",
        currency="USD",
        price=500000,
        status="For Sale",
        description="Test description for asset 1",
        has_features=True,
    )
    asset2 = Asset(
        agent_id=created_agent.id,
        title="Test Asset 2",
        category="Vehicle",
        country="Germany",
        address="456 Main St",
        currency="EUR",
        price=30000,
        status="For Rent",
        description="Test description for asset 2",
        has_features=False
    )
    test_db.add_all([asset1, asset2])
    await test_db.flush()  # Ensure assets have IDs
    await test_db.commit()

    asset_id1 = asset1.id
    asset_id2 = asset2.id 
    cart_object_proto = {
        asset_id1: test_cart_object[0],
        asset_id2: test_cart_object[1],
    }

    # add items to the pre_offload set
    await redis_client.set(cart_pre_offload_key, json.dumps(cart_object_proto))
    
    # wait until the data has been propagated
    for _ in range(TEST_CART_OFFLOAD_SCHEDULE+10):
        cart_data_exists = await redis_client.get(cart_key)
        if cart_data_exists:
            break
        await asyncio.sleep(1)

    # Confirm pre-offload is deleted
    assert not await redis_client.exists(cart_pre_offload_key)
    # check that those items are in the cart set
    # wait for ttl seconds to confirm expiration
    cart_data = json.loads(await redis_client.get(cart_key))
    assert cart_data[f'{asset_id1}']['price'] == cart_object_proto[asset_id1]['price']
    assert cart_data[f'{asset_id2}']['price'] == cart_object_proto[asset_id2]['price']
    await asyncio.sleep(TEST_CART_TTL+1)
    assert not await redis_client.get(cart_key)
    
    # confirm that data persists in the database
    query = await test_db.execute(
        select(CartItem).where(CartItem.user_id == test_user_id)
    )
    results = query.scalars().all()
    assert len(results) == 2
    assert {item.asset_id for item in results} == {asset_id1, asset_id2}