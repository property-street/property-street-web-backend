import json
import asyncio
from typing import Dict
from fastapi import WebSocket, WebSocketException, status
from redis.asyncio import Redis, client

from .utils import handle_pending_trx
from . import agent_specific_channels, generic_channels
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.ws_init import websocket_logger
from property_street_backend.config.redis_connection_manager import redis_pool_instance
from property_street_backend.config.postgres_connection_manager import get_async_session
from property_street_backend.app.controllers.chat.pubsub_chat_handler import pubsub_chat_handler
from property_street_backend.app.controllers.asset_request.pubsub_request_handler import pubsub_request_handler
from property_street_backend.app.controllers.roommate_finder.pubsub_roommate_handler import pubsub_roommate_handler

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.redis: Redis = redis_pool_instance()
        self.user_pubsubs: Dict[int, client.PubSub] = {}
        self.listener_tasks: Dict[int, asyncio.Task] = {}
        self.pending_trx_tasks: Dict[int, asyncio.Task] = {}
        self.db = get_async_session()
        
    async def connect(self, websocket: WebSocket, user_id: int, is_agent: bool = False, last_n_timestamp: int = None):
        self.active_connections[user_id] = websocket

        # Create unique pubsub instance per user
        pubsub = self.redis.pubsub()
        self.user_pubsubs[user_id] = pubsub
        
        # addition of generic subscription channels 
        channel_list = list(generic_channels.values())

        if user_id != -1: # for authenticated users
            # addition of the user specific channel
            channel_list.append(f"user:{user_id}")

            if is_agent: # addition of agent specific channel if the user is an agent
                channel_list += list(agent_specific_channels.values())

            # start pending transaction task
            pending_trx_task = asyncio.create_task(handle_pending_trx(self.db, self.redis, user_id, last_n_timestamp, is_agent, websocket))
            self.pending_trx_tasks[user_id] = pending_trx_task
        
        # subscribe to channels
        await pubsub.subscribe(*channel_list)

        # Start channel listening task
        listener_task = asyncio.create_task(self._pubsub_listener(user_id, pubsub))
        self.listener_tasks[user_id] = listener_task
    
        if DEBUG:
            websocket_logger.info(f'**Websocket connection completed for user:{user_id} with subscribed channels: {channel_list}')
    
    async def disconnect(self, user_id: int):
        # Cleanup WebSocket
        self.active_connections.pop(user_id, None)

        # Cleanup PubSub
        pubsub: client.PubSub = self.user_pubsubs.pop(user_id, None)
        if pubsub:
            try:
                await pubsub.unsubscribe()
                await pubsub.close()
            except Exception as e:
                print(f"PubSub cleanup error for user {user_id}: {e}")

        # Cancel pubsub listener task
        task: asyncio.Task = self.listener_tasks.pop(user_id, None)
        if task:
            task.cancel()

        # Cancel tasks for authenticated sockets
        if user_id != -1:
            # Cancel pending trx task
            task: asyncio.Task = self.pending_trx_tasks.pop(user_id, None)
            if task:
                task.cancel()

    async def _pubsub_listener(self, user_id: int, pubsub: client.PubSub):
        websocket = self.active_connections.get(user_id)
        if not websocket:
            return

        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    raw = message['data']
                    if isinstance(raw, bytes):
                        raw = raw.decode()
                    await self.pubsub_message_dispatcher(websocket, raw)
                    # await websocket.send_text(raw)
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            # Normal cleanup on disconnect
            pass
        except Exception as e:
            print(f"Redis listener error for {user_id}: {e}")
            await self.disconnect(user_id)

    async def send_to_user(self, user_id: int, message: dict):
        if user_id == -1:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        await self.redis.publish(f"user:{user_id}", json.dumps(message))

    async def pubsub_message_dispatcher(self, websocket: WebSocket, data: str):
        parsed_data: dict = json.loads(data)
        category = parsed_data.get('category')

        if category == 'chat':
            await pubsub_chat_handler(websocket, parsed_data, self.redis, self.send_to_user)
        elif category == 'asset_request':
            await pubsub_request_handler(websocket, parsed_data, self.redis)
        elif category == 'roommates_finder':
            await pubsub_roommate_handler(websocket, parsed_data)


manager = ConnectionManager()
