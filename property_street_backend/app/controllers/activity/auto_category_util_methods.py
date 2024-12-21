import json
import redis.asyncio as redis
from property_street_backend.log_config.logger_config import log_message

async def handle_newly_created_asset_expiry(
    expired_key: str,
    redis_client: redis.Redis
) -> dict:

    hash_key = "newly_created_asset"
    hset_key = "auto_category"
    
    try:
        # Extract the asset ID from the expired key
        asset_id = int(expired_key.split(':')[-1])

        # Remove the ID from the Redis set
        id_removed_from_set = await redis_client.srem(hash_key, asset_id)
        if id_removed_from_set:
            log_message(
                log_type='success',
                message=f"Removed asset ID {asset_id} from 'newly_created_asset' set."
            )

        # Update the HSET
        auto_category = await redis_client.hget(hset_key, hash_key)
        if auto_category:
            collection = json.loads(auto_category)
            data_removed_from_collection = collection.pop(str(asset_id), None)
            if data_removed_from_collection:
                log_message(
                    log_type='success',
                    message=f"Removed data associated with asset ID {asset_id} from HSET."
                )
            else:
                log_message(
                    log_type='info',
                    message=f"No data found for asset ID {asset_id} in HSET."
                )
            
            # Update the HSET with what's left
            await redis_client.hset(
                hset_key,
                hash_key,
                json.dumps(collection)
            )

        return {
            "success": True,
            "message": f"Expiry handling completed for asset ID {asset_id}."
        }

    except Exception as e:
        log_message(
            log_type='error',
            message=f"Error while handling expiry for asset ID from key {expired_key}: {e}"
        )
        return {
            "success": False,
            "error": str(e)
        }
