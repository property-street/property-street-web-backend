import asyncio, logging, json, time
import redis.asyncio as redis
from fastapi import (
    WebSocket, 
    WebSocketDisconnect, 
)
from datetime import datetime
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession


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


gen_pool_key = 'gen_pool'


async def websocket_endpoint(
    websocket: WebSocket, 
    client_id: int, 
    redis_client: redis.Redis,
):
    await websocket.accept()
    pubsub = redis_client.pubsub()

    try:
        # The server subscribes to a channel named after the client_id.
        await pubsub.subscribe(client_id)

        # Continuously checks for new messages on the Redis Pub/Sub channel
        await data_reader(
            pubsub=pubsub,
            websocket=websocket,
            redis_client=redis_client
        )
       
        # Runs continuously in the background, 
        # fetching messages from the Redis Pub/Sub channel 
        # and forwarding them to the WebSocket client.
        reader_task = asyncio.create_task(data_reader())

        # Socket.send recipient that continuously waits for messages from the WebSocket client.
        # Handles incoming messages from the WebSocket client, 
        # publishes them to the Redis channel, 
        # and sends an acknowledgment back to the client.
        while True: 
            # data received
            data = await websocket.receive_text()

            # sends data to the channel according to the message structure
            await data_channeler(
                data = data,
                redis_client = redis_client,
            )
            
            # redundant/ confirmation that the message has been received
            # await websocket.send_text(f"Message received: {data}") 
    
    except WebSocketDisconnect:
        await pubsub.unsubscribe(client_id)
        reader_task.cancel()
        if DEBUG:
            websocket_logger.error(f"Client #{client_id} disconnected", exc_info=True)
    
    finally:
        # handle pending transactions
        await handle_pending_trx(
            client_id=client_id,
            redis_client=redis_client,
            websocket=websocket,
        )


async def data_reader(
    pubsub,
    websocket: WebSocket,
    redis_client: redis.Redis,
): # pubsub channel recipient
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True)
        message_obj = message['data'].decode('utf-8')
        message_type = message_obj['data']['type']
        recipient_id = message_obj['data']['recipient_id']
        recipient_id_str = str(recipient_id)
        sender_id = message_obj['data']['sender_id']
        sender_id_str = str(sender_id)
        
        # get the gen_pool set
        gen_pool_exists = await redis_client.exists(gen_pool_key)
        if gen_pool_exists:
            gen_pool = json.loads(await redis_client.get(gen_pool_key))
        else:
            gen_pool = {}
        
        if message_type=='incoming_message':
            # send the data
            try:
                await websocket.send_text(message_obj)
                
                if DEBUG:
                    websocket_logger.info("Message sent successfully!")

                # update the data structure as message is sent/delivered
                message_obj['data']['status'] = 'delivered'
                
                # update the sender's channel with the new DS
                try:          
                    sender_id = message_obj['data']['sender_id']
                    sender_id_str = str(sender_id)
                    await redis_client.publish(sender_id,message_obj)
                except Exception as e:
                    # when message fails to send to the sender
                    await add_pending_msg_to_pool(
                        gen_pool = gen_pool,
                        message_obj=message_obj,
                        redis_client=redis_client,
                        gen_pool_key=gen_pool_key,
                        user_id_str=sender_id_str,
                    )
            except Exception as e:
                # when message fails to reach the recipient
                await add_pending_msg_to_pool(
                    gen_pool = gen_pool,
                    message_obj=message_obj,
                    redis_client=redis_client,
                    gen_pool_key=gen_pool_key,
                    user_id_str=recipient_id_str,
                )
                
                if DEBUG:
                    websocket_logger.error(f"Failed to send message: {e}", exc_info=True)
                
                # log the message
                log_message(
                    log_type = 'error',
                    message = f"Failed to recipient-read to sender: {e}"
                )
        elif message_type=='message_read':
            # send the read notification to sender
            try:
                await websocket.send_text(message_obj)
                
                if DEBUG:
                    websocket_logger.info("Message read sent successfully to sender!")

                # update the data structure as message is sent/delivered
                message_obj['data']['status'] = 'read'
                
            except Exception as e:
                # when message fails to reach the recipient
                await add_pending_msg_to_pool(
                    gen_pool = gen_pool,
                    message_obj=message_obj,
                    redis_client=redis_client,
                    gen_pool_key=gen_pool_key,
                    user_id_str=sender_id_str,
                )
                
                if DEBUG:
                    websocket_logger.error(f"Failed to notify sender of message read: {e}", exc_info=True)
                
                # log the message
                log_message(
                    log_type = 'error',
                    message = f"Failed to notify sender of message read: {e}"
                )

        await asyncio.sleep(0.01)


async def data_channeler(
    data,
    redis_client,
):
    if data['type'] == 'incoming_message':
        recipient_id = data['recipient_id']
        # publish the data to the recipient 
        await redis_client.publish(recipient_id, data)
    elif data['type'] == 'message_read':
        sender_id = data['sender_id']
        # publish the data to the sender 
        await redis_client.publish(sender_id, data)


async def add_pending_msg_to_pool(
    gen_pool: dict,
    message_obj: dict,
    redis_client: redis.Redis,
    gen_pool_key: str,
    user_id_str: str,
):
    # make the indicator true
    gen_pool[user_id_str]['pending']['messages'] = True

    # check that the pending messages for the user exists / or create one
    pending_messages = gen_pool[user_id_str]['messages']
    if not pending_messages:
        pending_messages = []

    # append the message to the pool 
    pending_messages.append(message_obj)

    # save the modified messages to the pool
    await redis_client.set(gen_pool_key,json.dumps(gen_pool))


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
