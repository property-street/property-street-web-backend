from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils.offload_chat_data import offload_dialogue
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG



async def offload_messages(
    redis_client: Redis,
    db: AsyncSession,
):
    try:
        cursor = b"0"

        # Fetch all keys matching chat pattern
        # map each cart_items to the user_id in the cart_data hash map
        while cursor:
            cursor, keys = await redis_client.scan(cursor, match="chat_*", count=1000)
            
            if not keys:
                if DEBUG: 
                    logger.info("No more keys to process")
                break  
            
            for dialogue_key in keys:
                dialogue_key: bytes
                await offload_dialogue(
                    redis_client=redis_client,
                    db = db,
                    dialogue_key = dialogue_key.decode()
                )  
    except Exception as e:
        e_msg = f'Error offloading cached chats! Reason: {e}'
        if DEBUG:
            logger.error(e_msg)
