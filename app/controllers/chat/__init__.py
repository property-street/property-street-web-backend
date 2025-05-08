import json
from redis.asyncio import Redis

def chat_dialogue_hset_key(sender_id:int, recipient_id:int, /)->str:
    """Accepts a sender and recipient id, and returns a hset key used to hold cached data for a dialogue chat.

    Args:
        sender_id (int): sender's user id
        recipient_id (int): recipient's user id

    Returns:
        str: hset key used to query redis cache.
    """
    return f'chat_{min(sender_id,recipient_id)}_{max(sender_id,recipient_id)}'

async def get_or_create_cached_chat(recipient_id:int, sender_id:int, /, redis_client: Redis) -> dict:
    """Attempts to retrieve a chat object between two users if it exists, else
    returns and empty object

    Args:
        recipient_id (int): id of the chat recipient
        sender_id (int): id of the chat sender
        redis_client (Redis): redis session client

    Returns:
        dict: hash map of timestamp in milliseconds or an empty one
    """
    cached_hset_key = chat_dialogue_hset_key(sender_id, recipient_id)
    cached_chat = await redis_client.hget(cached_hset_key, 'chat_object')
    return json.loads(cached_chat) if cached_chat else {}           
