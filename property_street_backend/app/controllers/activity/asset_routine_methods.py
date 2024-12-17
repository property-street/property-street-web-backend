import asyncio
from property_street_backend.log_config.logger_config import (
    log_message
)



async def asset_auto_category_expiry(redis_client):
    print("**app started")

    try:
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
                                log_message(
                                    log_type='success',
                                    message=f"Removed asset ID {asset_id} from 'newly_created_asset' set."
                                )
                    # Optional: sleep for cooperative multitasking
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                log_message(
                    log_type='info',
                    message="Redis Pub/Sub listener shut down gracefully."
                )

        # Initialize Pub/Sub and a stop event
        pubsub = redis_client.pubsub()
        stop_event = asyncio.Event()
        listener_task = asyncio.create_task(
            run_pubsub_listener(pubsub, stop_event)
        )
    except Exception as e:
        # Stop the Pub/Sub listener and cleanup
        stop_event.set()
        await listener_task
        await pubsub.aclose()
        # Log unexpected errors
        log_message(
            log_type='error',
            message=f"Failed to process expired key: {e}"
        )

