import asyncio
from redis.asyncio import Redis

from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.config.settings import (
    DEBUG,
)
from property_street_backend.app.controllers.cache_expiration.expiry_pubsub_listener import run_cache_db_expiry_listener



async def cache_expiry_initializer(redis_client: Redis):
    if DEBUG:
        print("**Cache expiry invoked")

    try:
        # Initialize Pub/Sub and a stop event
        # create a task with the pubsub listener
        pubsub = redis_client.pubsub()
        stop_event = asyncio.Event()
        listener_task = asyncio.create_task(
            run_cache_db_expiry_listener(pubsub, stop_event, redis_client)
        )

        if DEBUG:
            print("**Cache expiry listener initialized")
        
        # return listener_task, stop_event, pubsub
    except Exception as e:
        # Log unexpected errors
        log_message(
            log_type='error',
            message=f"Unexpected error in cache expiry initializer: {e}"
        )
    finally:
        # Stop the Pub/Sub listener and cleanup
        stop_event.set() # signal the listener to shutdown
        await listener_task # wait for it to finish
        await pubsub.aclose() # close the pubsub connection
