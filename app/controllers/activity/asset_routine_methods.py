import json
from datetime import datetime
from redis.asyncio import Redis

from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import (
    log_message
)


newly_created_hash_key = "newly_created_asset"
auto_category_hset_key = "auto_category"

async def create_or_update_newly_created_asset_cache(
    asset_id: int, 
    asset_data: dict, 
    redis_client: Redis,
    newly_created: bool,
    expiry_seconds:int,
):
    """
    Cache newly created asset details in Redis.

    :param asset_id: Unique ID of the asset.
    :param asset_data: Dictionary containing the asset details.
    :param expiry_seconds: Expiration time in seconds for the asset cache.
    """
    hash_key = newly_created_hash_key
    hset_key = auto_category_hset_key

    # serialize datetime values
    date_fields = ['created_at', 'datetime_declined']
    for field in date_fields:
        value = asset_data[field]
        if isinstance(value, datetime):
            asset_data[field] = value.isoformat()

    asset_data_to_str = json.dumps(asset_data)

    # Create a specific key for the asset and set an expiry
    asset_key = f'{hash_key}:{asset_id}'

    try:
        asset_exists = await redis_client.exists(asset_key)
        
        if newly_created:
            # Add the asset ID to the tracking set
            await redis_client.sadd(hash_key, asset_id)

            await redis_client.set(asset_key, asset_data_to_str, ex=expiry_seconds)

        if newly_created or asset_exists:
            # Add or update the `auto_category` HSET
            existing_assets = await redis_client.hget(
                hset_key, 
                hash_key
            )
            
            # Parse existing-assets, an create or update object
            loaded_asset = json.loads(existing_assets) if existing_assets else {}
            loaded_asset[str(asset_id)] = asset_data

            # Update the HSET with the updated object
            await redis_client.hset(
                hset_key, 
                hash_key, 
                json.dumps(loaded_asset)
            )


        s_message=f"Asset {asset_id} cached successfully."
        log_message(
            log_type = 'success',
            message = s_message
        )
        if DEBUG:
            logger.info(s_message)

    except Exception as e:
        e_message=f"Error caching asset {asset_id}: {e}"
        log_message(
            log_type = 'success',
            message = e_message
        )
        if DEBUG:
            logger.error(e_message)
