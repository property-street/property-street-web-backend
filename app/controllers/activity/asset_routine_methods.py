import json
import asyncio
import redis.asyncio as redis

from property_street_backend.log_config.logger_config import (
    log_message
)


async def create_or_update_newly_created_asset_cache(
    asset_id: int, 
    asset_data: dict, 
    redis_client: redis.Redis,
    newly_created: bool,
    expiry_seconds:int,
):
    """
    Cache newly created asset details in Redis.

    :param asset_id: Unique ID of the asset.
    :param asset_data: Dictionary containing the asset details.
    :param expiry_seconds: Expiration time in seconds for the asset cache.
    """
    hash_key = "newly_created_asset"
    hset_key = "auto_category"

    try:
        asset_exists = await redis_client.exists(f'{hash_key}:{asset_id}')
        
        if newly_created:
            # Serialize the asset data to a JSON string
            asset_json = json.dumps(asset_data)

            # Add the asset ID to the tracking set
            await redis_client.sadd(hash_key, asset_id)

            # Create a specific key for the asset and set an expiry
            asset_key = f'{hash_key}:{asset_id}'
            await redis_client.set(asset_key, asset_json, ex=expiry_seconds)

        if newly_created or asset_exists:
            # Add or update the `auto_category` HSET
            existing_assets_json = await redis_client.hget(
                hset_key, 
                hash_key
            )
            
            if existing_assets_json:
                # Parse the existing JSON string and append the new asset
                existing_assets = json.loads(existing_assets_json)
                existing_assets[str(asset_id)] = asset_data
            else:
                # If no data exists, start with the new asset
                existing_assets = { asset_id:asset_data }

            # Update the HSET with the updated list
            await redis_client.hset(
                hset_key, 
                hash_key, 
                json.dumps(existing_assets)
            )


        log_message(
            log_type='success',
            message=f"Asset {asset_id} cached successfully."
        )

    except Exception as e:
        log_message(
            log_type='success',
            message=f"Error caching asset {asset_id}: {e}"
        )
