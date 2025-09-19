import json
from redis.asyncio import Redis

from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from . import newly_created_asset_set_key, auto_category_hset_key
from property_street_backend.log_config.logger_config import log_message


async def handle_newly_created_asset_expiry(
    expired_key: str,
    redis_client: Redis
) -> dict:

    try:
        # Extract the asset ID from the expired key
        asset_id = int(expired_key.split(':')[-1])

        # Remove the ID from the Redis set
        id_removed_from_set = await redis_client.srem(newly_created_asset_set_key, asset_id)
        if id_removed_from_set and DEBUG:
            logger.info(f"Removed asset ID {asset_id} from 'newly_created_asset' set.")

        # Update the HSET
        auto_category = await redis_client.hget(auto_category_hset_key, newly_created_asset_set_key)
        if auto_category:
            collection = json.loads(auto_category)
            data_removed_from_collection = collection.pop(str(asset_id), None)

            if DEBUG:
                if data_removed_from_collection:
                    logger.info(f"Removed data associated with asset ID {asset_id} from HSET.")
                else:
                    logger.error(
                        message=f"No data found for asset ID {asset_id} in HSET."
                    )
            
            # Update the HSET with what's left
            await redis_client.hset(
                auto_category_hset_key,
                newly_created_asset_set_key,
                json.dumps(collection)
            )

        return {
            "success": True,
            "message": f"Expiry handling completed for asset ID {asset_id}."
        }

    except Exception as e:
        if DEBUG:
            logger.error(
                f"Error while handling expiry for asset ID from key {expired_key}: {e}"
            )
        return {
            "success": False,
            "error": str(e)
        }


async def handle_recent_set_expiry(
    expired_key: str,
    redis_client: Redis
) -> dict:

    trending_set_key = "trending_searches"
    
    try:
        # Extract the token from the expired key
        token = expired_key.removeprefix("recent_")  # Get the token part

        # Remove the token entry from the trending zset
        token_removed_from_zset = await redis_client.zrem(trending_set_key, token)
        if token_removed_from_zset:
            log_message(
                log_type='success',
                message=f"Removed {token} from {trending_set_key}"
            )

        return {
            "success": True,
            "message": f"Removed {token} from {trending_set_key}"
        }

    except Exception as e:
        log_message(
            log_type='error',
            message=f"Error while removing {token} from {trending_set_key}: {e}"
        )
        return {
            "success": False,
            "error": str(e)
        }
