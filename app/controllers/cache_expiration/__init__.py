import asyncio
import redis.asyncio as redis

from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.config.settings import (
    DEBUG,
)
from property_street_backend.app.controllers.cache_expiration.expiry_pubsub_listener import run_pubsub_listener



async def cache_expiry_initializer(redis_client: redis.Redis):
    if DEBUG:
        print("**cache expiry invoked")

    try:
        # Initialize Pub/Sub and a stop event
        # create a task with the pubsub listener
        pubsub = redis_client.pubsub()
        stop_event = asyncio.Event()
        listener_task = asyncio.create_task(
            run_pubsub_listener(pubsub, stop_event, redis_client)
        )

        if DEBUG:
            print("**cache expiry initialized")

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
