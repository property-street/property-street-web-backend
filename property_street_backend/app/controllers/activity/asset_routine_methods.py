import asyncio

from property_street_backend.clogs.logger_config import (
    log_message
)


async def asset_auto_category_expiry(redis_client):
    print("**gra")
    try:
        # Get Redis Pub/Sub instance
        pubsub = redis_client.pubsub()

        # Subscribe to the key event notifications channel
        await pubsub.psubscribe('__keyevent@0__:expired')
        
        log_message(
            log_type='success',
            message=f"Called routine"
        )

        # Listen for messages asynchronously
        while True:
            log_message(
                log_type='success',
                message=f"Came through"
            )
                
            # Get a message (non-blocking)
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

            if message:
                # Process the message
                if message['type'] == 'pmessage':
                    expired_key = message['data'].decode('utf-8')
                    if 'newly_created_asset' in expired_key:
                        asset_id = expired_key.split(':')[-1]
                        # Remove the ID from the Redis set
                        removed = await redis_client.srem('newly_created_asset', asset_id)
                        
                        if removed:
                            # Log the success message
                            log_message(
                                log_type='success',
                                message=f"Removed asset ID {asset_id} from 'newly_created_asset' set."
                            )

            # Optional sleep for cooperative multitasking
            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        # Handle graceful shutdown
        log_message(
            log_type='info',
            message="Redis Pub/Sub listener shut down gracefully."
        )
    except Exception as e:
        # Log unexpected errors
        log_message(
            log_type='error',
            message=f"Failed to process expired key: {e}"
        )

