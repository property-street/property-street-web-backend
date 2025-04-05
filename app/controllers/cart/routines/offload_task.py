import os
import json
import asyncio
from redis.asyncio import Redis
from sqlalchemy.sql import insert
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.database import get_db
from property_street_backend.app.celery_config import celery_app, redis_db
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.cart.models import CartItem
from property_street_backend.config.settings import TEST_CART_TTL, PROD_CART_TTL
from property_street_backend.app.initiator import redis_client as get_redis_client
from property_street_backend.tests.conftest import get_test_db, get_test_redis
from property_street_backend.config.connection_manager import _redis_instances


async def get_db_based_on_context(env):
    if env == 'test':
        db = await get_test_db().__anext__()
    else:
        db = await get_db().__anext__()
    return db

async def get_redis_based_on_context(env):
    if env == 'test':
        async for redis_client in get_test_redis():
            break
    else:
        redis_client = await get_redis_client().__anext__()
    return redis_client


LOCK_KEY = "cart_offload_lock"

async def acquire_lock(redis_client: Redis):
    """Acquire a lock to ensure only one instance runs."""
    return await redis_client.set(
        LOCK_KEY, 
        "locked", 
        nx=True
    )

async def release_lock(redis_client: Redis):
    """Release the lock after task completion."""
    await redis_client.delete(LOCK_KEY)

@celery_app.task
def routine(env):
    new_loop = False  # Flag to track if we create a new loop

    try:
        try:
            loop = asyncio.get_running_loop()  # Get the current event loop
        except RuntimeError:
            loop = asyncio.new_event_loop()  # Create a new loop if none exists
            asyncio.set_event_loop(loop)
            new_loop = True  # Mark that we created a new loop
        
        # Run the task in the loop
        loop.run_until_complete(run_task(env))
    
    finally:
        if new_loop:  # Only close if we created a new loop
            loop.close()

async def run_task(env):
    """Executes the offload task with a Redis lock."""
    # get the global _redis_instances and the instance key from the global object
    # get the redis instance based on the current context
    global _redis_instances
    redis_instance_key = f"{env}_{redis_db}"
    redis_client = await get_redis_based_on_context(env)

    if not await acquire_lock(redis_client):
        print("Another instance is already running. Skipping execution.")
        return

    try:
        # get the cart_ttl and db
        cart_ttl = TEST_CART_TTL if env == 'test' else PROD_CART_TTL
        db = await get_db_based_on_context(env)
        
        # call the offload function
        await handle_cart_offload(
            cart_ttl=cart_ttl,
            db = db,
            redis_client=redis_client,
        )
    finally:
        await release_lock(redis_client)
        await redis_client.aclose() # explicitly close the redis client
        _redis_instances.pop(redis_instance_key, None) # delete the entry off the global object


async def handle_cart_offload(
    cart_ttl: int,
    db: AsyncSession,
    redis_client: Redis,
):

    try:
        cursor = b"0"
        cart_data = {} # # { int:user_id -> { asset_id -> {quantity, asset_cover_url, asset_title, price} } }
        bulk_records = []
        keys_to_delete = set()  # Collect keys for bulk deletion


        # Fetch all keys matching cart pattern
        # map each cart_items to the user_id in the cart_data hash map
        while cursor:
            cursor, keys = await redis_client.scan(cursor, match="cart_pre_offload_*", count=1000)
            
            if not keys:
                break  # No more keys to process

            for key in keys:
                user_id = int(key.decode().split("_")[-1])  # Extract user ID from key
                cart_data[user_id] = await redis_client.get(key)  # Get the cart string
            
            keys_to_delete.update(keys)  # Store keys for deletion

        # loop over the cart_data
        # load the cart_items
        for user_id, cart_object_str in cart_data.items():
            loaded_cart_object = json.loads(cart_object_str)
            
            # loop over the loaded cart items
            # Make a cart item instance and add to bulk records
            for asset_id, cart_details in loaded_cart_object.items():
                cart_item = {
                    "asset_id": int(asset_id),
                    "quantity": cart_details.quantity,
                    "user_id": user_id
                }
                bulk_records.append(cart_item)
            
            # store the cart object string to the user_cart with expiry
            cart_key = f'cart_{user_id}'
            await redis_client.set(cart_key, cart_object_str, ex=cart_ttl)

        if bulk_records:
            stmt = insert(CartItem).values(bulk_records)
            await db.execute(stmt)  # Bulk insert
            await db.commit()

            # Bulk delete only after DB save is successful
            if keys_to_delete:
                await redis_client.unlink(*keys_to_delete)  # Non-blocking deletion

        # log the success
        log_message(
            'success',
            f'Successful offload of cart_pre_offload sets to the database.'
        )
    except Exception as e:
        # log the success
        log_message(
            'error',
            f'Error offloading cart_pre_offload sets to the database. Reason: {e}'
        )
    

if __name__ == "__main__":
    pass
#    async def check_redis():
#        async for redis_client in get_test_redis():
#            break
#        print(isinstance(redis_client,redis.Redis))
#    asyncio.run(check_redis())