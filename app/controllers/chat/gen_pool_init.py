import logging, json, time
import redis.asyncio as redis
from fastapi import (
    WebSocket, 
)
from datetime import datetime
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.exceptions import RedisError, ConnectionError, TimeoutError


from property_street_backend.app.models import (
    User,
    Thread,
    Message,
)
from property_street_backend.config.settings import (
    DEBUG
)
from property_street_backend.log_config.logger_config import (
    log_message
)
websocket_logger = logging.getLogger("websocket")




async def handle_chat(
    chat_obj: dict,
    websocket: WebSocket,
    redis_client: redis.Redis,
):
    """Handles a chat object on a channel

    Args:
        websocket (WebSocket): _description_
        redis_client (redis.Redis): _description_
        chat_obj (dict): contains data like the message_type, recipient and sender id, etc,.
    """
    message_type = chat_obj['type']
    recipient_id = chat_obj['recipient_id']
    
    
    if message_type=='incoming_message':
        try:
            # send the data to the recipient
            # update the status of the message to delivered
            recipient_id = chat_obj['recipient_id']
            await websocket.send_text(chat_obj)
            chat_obj['status'] = 'delivered'
            
            if DEBUG:
                websocket_logger.info(f"Message sent successfully to {recipient_id}!")
            
            try:          
                # update the sender's channel with the new chat-object
                sender_id = chat_obj['sender_id']
                await redis_client.publish(sender_id,chat_obj)
            except (ConnectionError, TimeoutError, RedisError) as e:
                await add_pending_msg_to_pool(
                    message_obj=chat_obj,
                    redis_client=redis_client,
                    user_id=sender_id,
                )
                # log the message
                log_message(
                    log_type = 'error',
                    message = f"Failed to send recipient-read to sender channel: {e}"
                )
        except (ConnectionError, TimeoutError, RedisError) as e:
            # when message fails to reach the recipient
            await add_pending_msg_to_pool(
                message_obj=chat_obj,
                redis_client=redis_client,
                user_id=recipient_id,
            )
            
            if DEBUG:
                websocket_logger.error(f"Failed to send message to user_{recipient_id}: {e}", exc_info=True)
            
            # log the message
            log_message(
                log_type = 'error',
                message = f"Failed to recipient-read to sender: {e}"
            )
    elif message_type=='message_read':
        try:
            # send the read notification to sender
            # update the data structure as message is sent/delivered
            await websocket.send_text(chat_obj)
            chat_obj['status'] = 'read'
            
            if DEBUG:
                websocket_logger.info("Message read sent successfully to sender!")
        except Exception as e:
            sender_id = chat_obj['sender_id']
            # when message fails to reach the recipient
            await add_pending_msg_to_pool(
                message_obj=chat_obj,
                redis_client=redis_client,
                user_id=sender_id,
            )
            
            if DEBUG:
                websocket_logger.error(f"Failed to notify sender of message read: {e}", exc_info=True)
            
            # log the message
            log_message(
                log_type = 'error',
                message = f"Failed to notify sender_{sender_id} of message read: {e}"
            )


async def add_pending_msg_to_pool(
    user_id: int,
    message_obj: dict,
    redis_client: redis.Redis,
):
    user_gen_pool_key = f'gen_pool_{user_id}'
    user_gen_pool = await redis_client.get(user_gen_pool_key)
    loaded_user_gen_pool = json.loads(user_gen_pool) if user_gen_pool else {}
    
    # make the indicator true
    loaded_user_gen_pool['pending']['_messages'] = True

    # check that the pending messages for the user exists / or create one
    pending_messages = loaded_user_gen_pool['pending'].get('message_list')
    pending_messages_list = pending_messages if pending_messages else []

    # append the message to the pool 
    pending_messages_list.append(message_obj)

    # save the modified messages to the pool
    await redis_client.set(user_gen_pool_key,json.dumps(loaded_user_gen_pool))


async def handle_pending_trx(
    client_id: int,
    redis_client: redis.Redis,
    websocket: WebSocket,
):
    gen_pool_exists = await redis_client.exists(gen_pool_key)
    if gen_pool_exists:
        gen_pool = json.loads(await redis_client.get(gen_pool_key))

        # check if any transaction belongs to the user
        if gen_pool[str(client_id)]:
            # check for pending messages
            if gen_pool[str(client_id)]['pending']['messages']:
                # get the message for the connected client
                pending_messages = gen_pool[str(client_id)]['messages']
                # send the message to the client
                websocket.send_text(pending_messages)

                # clear the user's entry of the pending pool
                await clear_user_entry_off_pool(
                    client_id= client_id,
                    gen_pool=gen_pool,
                    redis_client=redis_client,
                )


async def clear_user_entry_off_pool(
    client_id: int,
    gen_pool: dict,
    redis_client: redis.Redis
):
    try:
        # check if any transaction belongs to the user
        if gen_pool[str(client_id)]:
            # check for pending messages for the users
            if gen_pool[str(client_id)]['pending']['messages']:
                # delete the client's entry
                del gen_pool[str(client_id)]
                # update the redis set
                await redis_client.set(gen_pool_key,json.dumps(gen_pool))
    except Exception as e:
        if DEBUG:
            websocket_logger.error(f"Failed delete user message entry off pool: {e}", exc_info=True)
        
        # log the message
        log_message(
            log_type = 'error',
            message = f"Failed delete user message entry off pool: {e}"
        )


async def cache_message(
    redis_client: redis.Redis, 
    sender_id: int, 
    recipient_id: int, 
    message_obj: dict,
):
    key = f"msg_to_offload:{min(sender_id, recipient_id)}:{max(sender_id, recipient_id)}"
    timestamp = int(time.time())
    field = f"{sender_id}_{timestamp}"

    # add timestamp of the msg_obj
    message_obj['timestamp'] = timestamp
    
    # check if the field previously existed
    field_exists = await redis_client.hget(key, field)
    # Add or overwrite message to cache
    await redis_client.hset(key, field, json.dumps(message_obj))
    # if field is new, Append the key (timestamp) to a Redis list to maintain order
    if not field_exists:
        await redis_client.rpush(f"{key}:order", field)
    
    # get the ttl of the hset
    ttl = await redis_client.ttl(key)
    
    # If no TTL is set, initialize a TTL
    if ttl == -1:
        await redis_client.expire(key, 1800)  # 30 minutes


async def offload_messages(
    redis_client: redis.Redis,
    sender_id: int,
    recipient_id: int,
    db: AsyncSession,
):
    key = f"msg_to_offload:{min(sender_id, recipient_id)}:{max(sender_id, recipient_id)}"
    order_key = f"{key}:order"

    # Step 1: Fetch all cached messages in order
    fields = await redis_client.lrange(order_key, 0, -1)
    if not fields:
        return  # No messages to offload

    messages = [json.loads(await redis_client.hget(key, field)) for field in fields]

    # Step 2: Fetch or create the Thread
    thread_stmt = (
        select(Thread)
        .where(
            (Thread.participants.any(User.id == sender_id))
            & (Thread.participants.any(User.id == recipient_id))
        )
    )
    thread_result = await db.execute(thread_stmt)
    thread = thread_result.scalars().first()

    if not thread:
        thread = Thread(participants=[sender_id, recipient_id], created_at=datetime.utcnow())
        db.add(thread)
        await db.commit()
        await db.refresh(thread)

    # Step 3: Prepare messages for bulk operations
    new_messages = []
    update_operations = []

    for message in messages:
        if "db_id" in message:
            # Existing message, update fields
            update_stmt = (
                update(Message)
                .where(Message.id == message["db_id"])
                .values(
                    text_content=message["text_content"],
                    updated_timestamp=message["updated_timestamp"],
                    status=message["status"],
                )
            )
            update_operations.append(update_stmt)
        else:
            # New message, create instance
            new_message = Message(
                thread_id=thread.id,
                sender_id=message["sender_id"],
                recipient_id=message["recipient_id"],
                content=message["content"],
                created_at=message["timestamp"],
                status=message["status"],
            )
            new_messages.append(new_message)

    # Step 4: Execute bulk operations
    if new_messages:
        db.add_all(new_messages)
    for stmt in update_operations:
        await db.execute(stmt)

    await db.commit()

    # Step 5: Cleanup Redis
    await redis_client.delete(key)
    await redis_client.delete(order_key)
