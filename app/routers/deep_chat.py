import json
import time
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket , WebSocketDisconnect

from property_street_backend.app.controllers.ws_init.ws_manager import manager
from property_street_backend.config.context_sessions import get_redis_based_on_context
from property_street_backend.app.controllers.ws_init.real_time_initiator import ws_reception_handler

router = APIRouter(prefix='/deep-chat')

@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, chat_id: str = None):
    
    await manager.connect(websocket, user_id, chat_id)

    try:
        while True:
            data = await websocket.receive_text()
            await ws_reception_handler(data, manager)
    except WebSocketDisconnect:
        await manager.disconnect(user_id)