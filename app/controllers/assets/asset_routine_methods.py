from datetime import datetime, timezone
from redis.asyncio import Redis

from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import (
    log_message
)

# Redis keys for ID-based caching
newly_created_asset_zset_key = "newly_created_asset_ids"


async def add_asset_id_to_newly_created_cache(
    asset_id: int, 
    redis_client: Redis,
    expiry_seconds: int,
):
    """
    Add an asset ID to the newly created assets cache (ID-based).
    
    :param asset_id: Unique ID of the asset.
    :param redis_client: Redis client instance.
    :param expiry_seconds: Expiration time in seconds for the cache entries.
    """
    try:
        # Get current timestamp for sorting (higher timestamp = newer)
        timestamp = datetime.now(timezone.utc).timestamp()
        
        # Add asset ID to sorted set with timestamp as score (descending order)
        await redis_client.zadd(
            newly_created_asset_zset_key, 
            {asset_id: timestamp}
        )
        
        # Set expiry on the entire sorted set
        await redis_client.expire(newly_created_asset_zset_key, expiry_seconds)
        
        s_message = f"Asset ID {asset_id} added to newly created cache."
        log_message(log_type="success", message=s_message)
        if DEBUG:
            logger.info(s_message)

    except Exception as e:
        e_message = f"Error adding asset ID {asset_id} to cache: {e}"
        log_message(log_type="error", message=e_message)
        if DEBUG:
            logger.error(e_message)


async def remove_asset_id_from_newly_created_cache(
    asset_id: int,
    redis_client: Redis,
):
    """
    Remove an asset ID from the newly created assets cache.
    
    :param asset_id: Unique ID of the asset.
    :param redis_client: Redis client instance.
    """
    try:
        # Remove the asset ID from the sorted set
        await redis_client.zrem(newly_created_asset_zset_key, asset_id)
        
        s_message = f"Asset ID {asset_id} removed from newly created cache."
        log_message(log_type="success", message=s_message)
        if DEBUG:
            logger.info(s_message)

    except Exception as e:
        e_message = f"Error removing asset ID {asset_id} from cache: {e}"
        log_message(log_type="error", message=e_message)
        if DEBUG:
            logger.error(e_message)


async def get_newly_created_asset_ids(
    redis_client: Redis,
    offset: int = 0,
    limit: int = 20,
):
    """
    Get asset IDs from the newly created assets cache.
    Returns IDs in descending order (newest first).
    
    :param redis_client: Redis client instance.
    :param offset: Pagination offset.
    :param limit: Number of IDs to retrieve.
    :return: List of asset IDs.
    """
    try:
        # Get IDs from sorted set in descending order (highest score first = newest)
        asset_ids = await redis_client.zrevrange(
            newly_created_asset_zset_key,
            offset,
            offset + limit - 1
        )
        
        # Convert bytes to int if necessary
        return [int(aid) if isinstance(aid, bytes) else int(aid) for aid in asset_ids]

    except Exception as e:
        e_message = f"Error retrieving newly created asset IDs: {e}"
        log_message(log_type="error", message=e_message)
        if DEBUG:
            logger.error(e_message)
        return []


async def clear_newly_created_asset_cache(redis_client: Redis):
    """
    Clear all asset IDs from the newly created assets cache.
    
    :param redis_client: Redis client instance.
    """
    try:
        await redis_client.delete(newly_created_asset_zset_key)
        
        s_message = "Newly created assets cache cleared."
        log_message(log_type="success", message=s_message)
        if DEBUG:
            logger.info(s_message)

    except Exception as e:
        e_message = f"Error clearing newly created asset cache: {e}"
        log_message(log_type="error", message=e_message)
        if DEBUG:
            logger.error(e_message)
