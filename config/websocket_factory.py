from typing import Optional
from fastapi import WebSocket

authenticated_ws = {}  # dictionary of connected WebSocket clients

agents_ws = {}  # Set of connected WebSocket clients

unauthenticated_ws = set()

async def broadcast_to_clients(connected_websockets:set, data:str):
    # Broadcast to all clients
    for ws in connected_websockets:
        await ws.send_text(data.decode())

def get_client_socket_from_factory(*,client_id:int) -> Optional[WebSocket]:
    return authenticated_ws.get(client_id, None)