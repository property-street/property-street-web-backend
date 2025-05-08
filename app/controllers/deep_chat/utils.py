from .ws_manager import manager

def get_redis_pubsub(redis_client):
    pubsub = redis_client.pubsub()
    return pubsub

async def listen_to_channel(channel: str, user_id: str):
    pubsub = get_redis_pubsub()
    await pubsub.subscribe(channel)
    
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True)
        if message:
            await manager.send_personal_message(message['data'].decode(), user_id)