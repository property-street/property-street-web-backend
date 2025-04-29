import asyncio
import redis.asyncio as redis

from property_street_backend.log_config.logger_config import (
    log_message
)
from .dispatch_expiry_case import dispatch_expiry_case


async def run_cache_db_expiry_listener(
    pubsub: redis.client.PubSub, 
    stop_event: asyncio.Event,
    redis_client: redis.Redis,
):
    """This function subscribes to a redis expiry event
        and calls a custom dispatcher function when one occurs

    Args:
        pubsub (_type_): _description_
        stop_event (_type_): _description_
        redis_client (redis.Redis): redis.Redis instance
    """
    try:
        CACHE_DB = redis_client.connection_pool.connection_kwargs['db']
        await pubsub.psubscribe(f'__keyevent@{CACHE_DB}__:expired')

        while not stop_event.is_set():
            try:
                # Get a message (non-blocking)
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'pmessage':
                    expired_key = message['data'].decode('utf-8')

                    # run the dispatcher
                    await dispatch_expiry_case(expired_key, redis_client)

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
