import asyncio
from redis.asyncio import Redis

from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.config.settings import (
    DEBUG,
)
from property_street_backend.app.controllers.cache_expiration.expiry_pubsub_listener import run_cache_db_expiry_listener
from property_street_backend.app.initiator import logger



async def cache_expiry_initializer(redis_client: Redis):
    if DEBUG:
        logger.info("**Cache expiry initializer starting")

    try:
        await redis_client.config_set("notify-keyspace-events", "Ex")

        pubsub = redis_client.pubsub()
        stop_event = asyncio.Event()

        # ✅ Run the listener as a long-lived background task
        listener_task = asyncio.create_task(
            run_cache_db_expiry_listener(pubsub, stop_event, redis_client)
        )

        # ✅ Return to be managed outside
        return listener_task, stop_event, pubsub

    except Exception as e:
        logger.error(f"Unexpected error in cache expiry initializer: {e}", exc_info=True)
        log_message(log_type='error', message=str(e))
        return None, None, None
