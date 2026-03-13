import asyncio

from server.websocket.server import run_websocket_server


if __name__ == "__main__":
    asyncio.run(run_websocket_server())
