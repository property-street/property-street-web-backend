from typing import Optional
from fastapi import WebSocket

client_authenticated_ws = None 

agents_ws = {}  # Set of connected WebSocket clients

unauthenticated_ws = None

def get_instance_ws() -> Optional[WebSocket]:
    return client_authenticated_ws if client_authenticated_ws and not client_authenticated_ws.client_state.name == "DISCONNECTED" else None