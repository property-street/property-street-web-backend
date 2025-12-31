import time
import asyncio
from redis.asyncio import Redis


from property_street_backend.app.celery_config import (
    redis_db,
    celery_app,
    agent_stall_notification_deletion_schedule_secs, 
)
from property_street_backend.config.context_sessions import (
    acquire_redis_lock,
    release_redis_lock,
)
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.config.redis_connection_manager import get_redis_instance


LOCK_KEY = "agent_notification_entry_delete_lock"


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
    async with get_redis_instance() as redis_client:
        if not await acquire_redis_lock(
            redis_client = redis_client,
            lock_key=LOCK_KEY,
            ex=agent_stall_notification_deletion_schedule_secs
        ):
            print("Another instance is already running. Skipping execution.")
            return

        try:
            # call the offload function
            await handle_deletion(
                redis_client=redis_client,
            )
        finally:
            await release_redis_lock(redis_client=redis_client, lock_key=LOCK_KEY)


async def handle_deletion(
    redis_client: Redis,
):
    try:
        now_ms = int(time.time() * 1000)  # current Unix timestamp in seconds
        await redis_client.zremrangebyscore("pend_pool_agent_notification", '-inf', now_ms-1)
        # log the success
        log_message(
            'success',
            f'Successfully deleted stall agent notification entries.'
        )
    except Exception as e:
        # log the success
        log_message(
            'error',
            f'Error deleted stall agent notification entries. Reason: {e}'
        )


if __name__ == "__main__":
    pass