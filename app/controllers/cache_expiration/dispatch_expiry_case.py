import redis.asyncio as redis

from property_street_backend.app.controllers.activity.auto_category_util_methods import (
    handle_newly_created_asset_expiry,
    handle_recent_set_expiry,
)

async def dispatch_expiry_case(
    expired_key: str,
    redis_client: redis.Redis,
):
    """
        This function calls a custom function to execute 
        utility functionalities when a redis cache is expired.
    """
    # Handle newly_created_asset expiration
    if 'newly_created_asset' in expired_key:
        await handle_newly_created_asset_expiry(
            expired_key=expired_key,
            redis_client=redis_client,
        )
    elif expired_key.startswith("recent_"):
        await handle_recent_set_expiry(
            expired_key=expired_key,
            redis_client=redis_client,
        )