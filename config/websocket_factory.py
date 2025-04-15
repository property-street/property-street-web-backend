connected_ws = {}  # Set of connected WebSocket clients

connected_agents_ws = {}  # Set of connected WebSocket clients

unauthenticated_ws = set()

async def broadcast_to_clients(connected_websockets:set, data:str):
    # Broadcast to all clients
    for ws in connected_websockets:
        await ws.send_text(data.decode())