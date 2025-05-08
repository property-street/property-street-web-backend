import json
import asyncio
from typing import Dict
from fastapi import WebSocket
from redis.asyncio import Redis, client


from property_street_backend.app.controllers.ws_init import websocket_logger
from property_street_backend.app.controllers.chat.pubsub_chat_handler import pubsub_chat_handler

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.redis = Redis(host="localhost", port=6379, db=1, decode_responses=True)
        self.user_pubsubs: Dict[int, client.PubSub] = {}
        self.listener_tasks: Dict[int, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, user_id: int, chat_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

        # Create unique pubsub instance per user
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"user:{user_id}", f"chat:{chat_id}")
        self.user_pubsubs[user_id] = pubsub

        # Start listening task
        listener_task = asyncio.create_task(self._pubsub_listener(user_id, pubsub))
        self.listener_tasks[user_id] = listener_task

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

        # Cancel listener task
        task: asyncio.Task = self.listener_tasks.pop(user_id, None)
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

    async def send_to_chat(self, chat_id: int, message: dict):
        await self.redis.publish(f"chat:{chat_id}", json.dumps(message))

    async def send_to_user(self, user_id: int, message: dict):
        await self.redis.publish(f"user:{user_id}", json.dumps(message))

    async def pubsub_message_dispatcher(self, websocket: WebSocket, data: str):
        parsed_data: dict = json.loads(data)

        if parsed_data.get('category') == 'chat':
            await pubsub_chat_handler(websocket, parsed_data, self.redis, self.send_to_user)


manager = ConnectionManager()
