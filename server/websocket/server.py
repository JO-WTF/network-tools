import asyncio

import websockets

from server.websocket.handler import handle_connection

WS_MAX_SIZE = 10 * 1024 * 1024


async def run_websocket_server(host="0.0.0.0", port=8765):
    async with websockets.serve(handle_connection, host, port, max_size=WS_MAX_SIZE):
        await asyncio.Future()
