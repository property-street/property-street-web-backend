from urllib.parse import parse_qs
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.database import get_db
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.ws_init import websocket_logger
from property_street_backend.app.controllers.ws_init.ws_manager import manager
from property_street_backend.app.controllers.ws_init.core import ws_reception_handler
from property_street_backend.app.controllers.auth import decode_user_from_token_optional

router = APIRouter(prefix='/ws', tags=['ws'])

@router.websocket("")
async def websocket_endpoint( websocket: WebSocket ):
    await websocket.accept()

    # Manually extract query parameters
    query_params = parse_qs(websocket.url.query)
    last_n_timestamp = query_params.get("last_n_timestamp", [None])[0]
    test_ping = query_params.get("test_ping", [None])[0]
    token = query_params.get("access_token", [None])[0]

    current_user = None
    if token:
        try:
            db = await anext(get_db(
                metadata_test_routine = False,
                skip_session_close = True,
            ))                
            current_user = await decode_user_from_token_optional(token,db)
        except Exception as e:
            if DEBUG:
                websocket_logger.info(f'** Error decoding user from token. Reason: {e}')

    client_id = current_user.id if current_user else -1
    is_agent = True if current_user and current_user.agent_profile else False

    if test_ping == 'true':
        await websocket.send_json({
            "type": "pong", 
            'token': token,
            'username': current_user.username if current_user else None,
            'last_n_timestamp': last_n_timestamp,
            'is_agent': is_agent
        })

    await manager.connect(
        websocket, 
        client_id, 
        is_agent, 
        int(last_n_timestamp) if last_n_timestamp else None
    ) 
    
    try:
        while True:
            data = await websocket.receive_text()
            if DEBUG:
                websocket_logger.info(f'**data received from client socket:{data}')
            await ws_reception_handler(data, manager)
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
    finally: 
        await db.close()