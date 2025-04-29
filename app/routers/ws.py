from typing import Optional
from redis.asyncio import Redis
from urllib.parse import parse_qs
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, WebSocket, Depends

from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.controllers.auth import TokenData, decode_user_from_token_optional
from property_street_backend.app.controllers.ws_init.real_time_initiator import websocket_initialiazer

router = APIRouter(prefix='/ws', tags=['ws'])

@router.websocket("/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    client_id: int,
    redis_client: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
):
    await websocket.accept()

    # Manually extract query parameters
    query_params = parse_qs(websocket.url.query)
    last_n_timestamp = query_params.get("last_n_timestamp", [None])[0]

    # Manually extract Authorization token
    token = websocket.headers.get("Authorization")
    current_user = None
    if token:
        try:
            current_user = await decode_user_from_token_optional(token.replace("Bearer ", ""))
        except Exception:
            pass

    # Proceed with chat logic
    await websocket.send_json({"type": "pong"})
    
    await websocket_initialiazer(
        websocket=websocket,
        client_id=client_id,
        is_agent= True if current_user.agent_profile else False,
        redis_client= redis_client,
        db=db,
        # optional keyword arguments
        last_n_timestamp = last_n_timestamp
    )