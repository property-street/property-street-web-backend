import json
import asyncio
import redis.asyncio as redis

from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.config.settings import (
    DEBUG,
)
from property_street_backend.app.controllers.activity.auto_category_util_methods import (
    handle_newly_created_asset_expiry,
    handle_recent_set_expiry,
)



async def asset_auto_category_expiry(redis_client):
    if DEBUG:
        print("**app started")

    try:
        # Helper function to run the Redis Pub/Sub listener
        async def run_pubsub_listener(
            pubsub, 
            stop_event
        ):
            try:
                CACHE_DB = redis_client.connection_pool.connection_kwargs['db']
                await pubsub.psubscribe(f'__keyevent@{CACHE_DB}__:expired')

                while not stop_event.is_set():
                    try:
                        # Get a message (non-blocking)
                        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                        if message and message['type'] == 'pmessage':
                            expired_key = message['data'].decode('utf-8')

                            # Handle newly_created_asset expiration
                            if 'newly_created_asset' in expired_key:
                                await handle_newly_created_asset_expiry(
                                    expired_key=expired_key,
                                    redis_client=redis_client,
                                )
                            if expired_key.startswith("recent_"):
                                await handle_recent_set_expiry(
                                    expired_key=expired_key,
                                    redis_client=redis_client,
                                )

                        # Optional: sleep for cooperative multitasking
                        await asyncio.sleep(0.1)

                    except redis.ConnectionError as e:
                        log_message(
                            log_type='error',
                            message=f"Redis connection error: {e}. Retrying..."
                        )
                        await asyncio.sleep(5)  # Retry after a delay

            except asyncio.CancelledError:
                log_message(
                    log_type='info',
                    message="Redis Pub/Sub listener shut down gracefully."
                )
            except Exception as e:
                log_message(
                    log_type='error',
                    message=f"Unexpected error in Pub/Sub listener: {e}"
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


async def create_or_update_newly_created_asset_cache(
    asset_id: int, 
    asset_data: dict, 
    redis_client: redis.Redis,
    newly_created: bool,
    expiry_seconds:int,
):
    """
    Cache newly created asset details in Redis.

    :param asset_id: Unique ID of the asset.
    :param asset_data: Dictionary containing the asset details.
    :param expiry_seconds: Expiration time in seconds for the asset cache.
    """
    hash_key = "newly_created_asset"
    hset_key = "auto_category"

    try:
        asset_exists = await redis_client.exists(f'{hash_key}:{asset_id}')
        
        if newly_created:
            # Serialize the asset data to a JSON string
            asset_json = json.dumps(asset_data)

            # Add the asset ID to the tracking set
            await redis_client.sadd(hash_key, asset_id)

            # Create a specific key for the asset and set an expiry
            asset_key = f'{hash_key}:{asset_id}'
            await redis_client.set(asset_key, asset_json, ex=expiry_seconds)

        if newly_created or asset_exists:
            # Add or update the `auto_category` HSET
            existing_assets_json = await redis_client.hget(
                hset_key, 
                hash_key
            )
            
            if existing_assets_json:
                # Parse the existing JSON string and append the new asset
                existing_assets = json.loads(existing_assets_json)
                existing_assets[str(asset_id)] = asset_data
            else:
                # If no data exists, start with the new asset
                existing_assets = { asset_id:asset_data }

            # Update the HSET with the updated list
            await redis_client.hset(
                hset_key, 
                hash_key, 
                json.dumps(existing_assets)
            )


        log_message(
            log_type='success',
            message=f"Asset {asset_id} cached successfully."
        )

    except Exception as e:
        log_message(
            log_type='success',
            message=f"Error caching asset {asset_id}: {e}"
        )
