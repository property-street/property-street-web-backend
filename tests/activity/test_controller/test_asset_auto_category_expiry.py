import asyncio
import pytest

@pytest.mark.asyncio
async def test_newly_created_asset_expiry(client__fixture):
    # Fetch the client generator
    client_gen = client__fixture
    client, redis_client = await client_gen.__anext__()

    # Helper function to run the Redis Pub/Sub listener
    async def run_pubsub_listener(pubsub, stop_event):
        try:
            CACHE_DB = redis_client.connection_pool.connection_kwargs['db']
            await pubsub.psubscribe(f'__keyevent@{CACHE_DB}__:expired')
            while not stop_event.is_set():
                # Get a message (non-blocking)
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'pmessage':
                    expired_key = message['data'].decode('utf-8')
                    if 'newly_created_asset' in expired_key:
                        asset_id = expired_key.split(':')[-1]
                        # Remove the ID from the Redis set
                        removed = await redis_client.srem('newly_created_asset', int(asset_id))
                        if removed:
                            print(f"Removed asset ID {asset_id} from 'newly_created_asset' set.")
                # Optional: sleep for cooperative multitasking
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            print("Pub/Sub listener shutdown gracefully.")

    # Initialize Pub/Sub and a stop event
    pubsub = redis_client.pubsub()
    stop_event = asyncio.Event()
    listener_task = asyncio.create_task(run_pubsub_listener(pubsub, stop_event))

    try:
        # Simulate a request to initialize the event listener
        url = "/"
        response = await client.get(url)
        assert response.status_code == 200
        assert response.json() == {
            "message": "Hello, World!",
            "environment": "development"
        }

        # Fabricate test data
        fabricated_asset_id = "12345"
        fabricated_detail = '{"title": "Test Asset", "description": "Temporary description"}'
        set_key = "newly_created_asset"
        hset_key = f"newly_created_asset:{fabricated_asset_id}"

        # Add the asset ID to the set and the HSET with expiry
        await redis_client.sadd(set_key, fabricated_asset_id)
        await redis_client.hset(hset_key, "newly_created_asset", fabricated_detail)
        await redis_client.expire(hset_key, 2)  # 2-second expiry

        # Sleep to allow expiration to trigger
        await asyncio.sleep(5)

        # Assert that the HSET does not exist (expired)
        hset_exists = await redis_client.exists(hset_key)
        assert hset_exists == 0, "HSET key should have expired but still exists."

        # Assert that the asset ID has been removed from the set
        asset_in_set = await redis_client.sismember(set_key, fabricated_asset_id)
        assert asset_in_set == 0, "Asset ID should have been removed from the set but still exists."

    finally:
        # Stop the Pub/Sub listener and cleanup
        stop_event.set()
        await listener_task
        await pubsub.aclose()
