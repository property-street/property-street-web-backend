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
        cacheable = (await redis_client.exists(asset_key)) or newly_created
        
        if newly_created:
            # Add the asset ID to the tracking set
            await redis_client.sadd(hash_key, asset_id)

            await redis_client.set(asset_key, asset_data_to_str, ex=expiry_seconds)

        if cacheable:
            # Add or update the `auto_category` HSET
            existing_assets = await redis_client.hget(
                hset_key, hash_key
            )
            
            # Parse existing-assets, an create or update object
            loaded_asset = json.loads(existing_assets) if existing_assets else {}
            loaded_asset[str(asset_id)] = asset_data

            # Update the HSET with the updated object
            await redis_client.hset(
                hset_key, hash_key, 
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


async def remove_asset_from_newly_created_asset_cache(
    asset_id: int,
    redis_client: Redis,
):
    """
    Remove an asset from all Redis caches created by
    create_or_update_newly_created_asset_cache.
    """
    hash_key = newly_created_hash_key
    hset_key = auto_category_hset_key

    asset_key = f"{hash_key}:{asset_id}"

    try:
        # 1️⃣ Remove the per-asset cache key
        await redis_client.delete(asset_key)

        # 2️⃣ Remove asset ID from the tracking set
        await redis_client.srem(hash_key, asset_id)

        # 3️⃣ Update the auto-category HSET
        existing_assets = await redis_client.hget(hset_key, hash_key)

        if existing_assets:
            loaded_assets = json.loads(existing_assets)

            # Remove this asset from the object
            if str(asset_id) in loaded_assets:
                del loaded_assets[str(asset_id)]

                if loaded_assets:
                    # Write back updated object
                    await redis_client.hset(
                        hset_key,
                        hash_key,
                        json.dumps(loaded_assets)
                    )
                else:
                    # No assets left → remove the HSET field entirely
                    await redis_client.hdel(hset_key, hash_key)

        s_message = f"Asset {asset_id} removed from cache successfully."
        log_message(
            log_type="success",
            message=s_message
        )
        if DEBUG:
            logger.info(s_message)

    except Exception as e:
        e_message = f"Error removing asset {asset_id} from cache: {e}"
        log_message(
            log_type="error",
            message=e_message
        )
        if DEBUG:
            logger.error(e_message)


async def remove_all_newly_created_assets_cache(
    redis_client: Redis,
):
    """
    Remove all newly created assets from Redis cache.
    """
    hash_key = newly_created_hash_key
    hset_key = auto_category_hset_key

    try:
        # 1️⃣ Get all tracked asset IDs
        asset_ids = await redis_client.smembers(hash_key)

        if asset_ids:
            # 2️⃣ Delete all per-asset keys
            asset_keys = [f"{hash_key}:{asset_id.decode() if isinstance(asset_id, bytes) else asset_id}"
                          for asset_id in asset_ids]

            await redis_client.delete(*asset_keys)

        # 3️⃣ Delete the tracking set itself
        await redis_client.delete(hash_key)

        # 4️⃣ Delete the auto-category HSET field
        await redis_client.hdel(hset_key, hash_key)

        s_message = "All newly created assets removed from cache successfully."
        log_message(
            log_type="success",
            message=s_message
        )
        if DEBUG:
            logger.info(s_message)

    except Exception as e:
        e_message = f"Error removing all newly created assets from cache: {e}"
        log_message(
            log_type="error",
            message=e_message
        )
        if DEBUG:
            logger.error(e_message)
        raise e


async def get_property_from_newly_created_asset(redis_client: Redis, id: int) -> dict|None:
    cached_obj = await redis_client.hget(auto_category_hset_key, newly_created_hash_key)
    loaded_cached_obj: dict = json.loads(cached_obj) if cached_obj else {}
    return loaded_cached_obj.get(str(id))