import time
import json


from property_street_backend.config.context_sessions import get_redis_based_on_context
from property_street_backend.config.websocket_factory import agents_ws


async def asset_request_channel_handler(message: str):
    """
    Handles incoming asset request messages and pings active agents while caching for inactive ones.

    :param message: JSON string with:
        {
            "description": str,
            "country": str,
            "city_or_town": str,
            "state_or_province": str,
            "street": str
        }
    """
    redis_client = await get_redis_based_on_context()

    timestamp_ms = int(time.time() * 1000)
    
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        # Optionally log or raise
        return

    # Add metadata
    payload["timestamp"] = timestamp_ms  
    payload["category"] = "notification"

    # Redis key for notification ZSET
    key = "pend_pool_agent_notification"

    # ZSET uses timestamp as the score for ordering
    await redis_client.zadd(key, {json.dumps(payload): timestamp_ms})

    # Broadcast to all active agent WebSocket connections
    for agent_ws in agent_ws:
        if agent_ws and not agent_ws.client_state.name == "DISCONNECTED":
            try:
                await agent_ws.send_json({
                    "event": "asset_request_notification",
                    "data": [payload] # list of payload
                })
            except Exception as e:
                # Optional: mark agent_ws for cleanup or log it
                pass