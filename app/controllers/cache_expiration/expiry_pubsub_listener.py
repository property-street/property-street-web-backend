import asyncio
from redis.asyncio import Redis, client, ConnectionError

from .dispatch_expiry_case import dispatch_expiry_case
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import (
    log_message
)

expiry_pubsub_loop_entered = 'expiry_pubsub_loop_entered'

async def run_cache_db_expiry_listener(
    pubsub: client.PubSub, 
    stop_event: asyncio.Event,
    redis_client: Redis,
):
    """This function subscribes to a redis expiry event
        and calls a custom dispatcher function when one occurs

    Args:
        pubsub (_type_): _description_
        stop_event (_type_): _description_
        redis_client (redis.Redis): redis.Redis instance
    """
    if DEBUG:
        logger.info("**Cache expiry task running...")
    
    try:
        # get the redis database and subscribe to expiry events.
        CACHE_DB = redis_client.connection_pool.connection_kwargs['db']
        await pubsub.psubscribe(f'__keyevent@{CACHE_DB}__:expired')
        

        while not stop_event.is_set():
            # if DEBUG:
            #     logger.info("**In Cache expiry notification loop!")
            
            # set an indicator that the loop has been entered.
            await redis_client.set(expiry_pubsub_loop_entered, '', nx=True)
            
            # Get a message (non-blocking)
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                if DEBUG:
                    logger.info(f"**Pubsub message: {message}")
            

                if message['type'] == 'pmessage':
                    expired_key = message['data'].decode('utf-8')
                    # run the dispatcher
                    await dispatch_expiry_case(expired_key, redis_client)

            # Optional: sleep for cooperative multitasking
            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        log_message(
            log_type='info',
            message="Redis Pub/Sub listener shut down gracefully."
        )
    except Exception as e:
        log_message(
            log_type='error',
            message=f"Unexpected error in run_cache_db_expiry_listener Pub/Sub: {e}"
        )
    finally:
        # delete the indicator initially set.
        await redis_client.delete(expiry_pubsub_loop_entered)
        # close the pubsub instance
        await pubsub.aclose()
        logger.info("Redis Pub/Sub connection closed")