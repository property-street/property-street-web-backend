from urllib.parse import parse_qs
from sqlalchemy import select
from fastapi import APIRouter, WebSocket

from property_street_backend.config.context_sessions import get_db_based_on_context, get_redis_based_on_context
from property_street_backend.app.controllers.auth import decode_user_from_token_optional
from property_street_backend.app.controllers.ws_init.real_time_initiator import websocket_initialiazer

router = APIRouter(prefix='/ws', tags=['ws'])

@router.websocket("/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
):
    await websocket.accept()

    # Manually extract query parameters
    query_params = parse_qs(websocket.url.query)
    last_n_timestamp = query_params.get("last_n_timestamp", [None])[0]
    test_ping = query_params.get("test_ping", [None])[0]

    # Manually extract database and redis_client
    # the metadata_test_routine should not run if this is a test environment
    # this session should enforce a close, as it would conflict the originator in a test environment
    async for db in get_db_based_on_context( metadata_test_routine = False, skip_session_close = True ):
        break
    async for redis_client in get_redis_based_on_context( skip_session_close = True ):
        break

    # Manually extract Authorization token
    bearer = websocket.headers.get("Authorization")
    token = bearer.replace("Bearer ", "") if bearer else ''
    current_user = None
    
    if token:
        try:
            current_user = await decode_user_from_token_optional(token,db)
        except Exception as e:
            print(e)

    client_id = current_user.id if current_user else None

    if test_ping == 'true':
        await websocket.send_json({
            "type": "pong", 
            'token': token,
            'username': current_user.username,
            'last_n_timestamp': last_n_timestamp
        })
    else: # Proceed with chat logic
        await websocket_initialiazer(
            websocket = websocket,
            client_id = client_id,
            is_agent = True if current_user and current_user.agent_profile else False,
            redis_client = redis_client,
            db = db,
            # optional keyword arguments
            last_n_timestamp = last_n_timestamp
        )
