from fastapi import APIRouter, WebSocket , WebSocketDisconnect

from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.ws_init import websocket_logger
from property_street_backend.app.controllers.ws_init.ws_manager import manager
from property_street_backend.app.controllers.ws_init.core import ws_reception_handler

router = APIRouter(prefix='/deep-chat')

@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    
    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            if DEBUG:
                websocket_logger.info(f'**data:{data} received from client socket')
            await ws_reception_handler(data, manager)
    except WebSocketDisconnect:
        await manager.disconnect(user_id)