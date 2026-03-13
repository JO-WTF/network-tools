import json


async def send_progress(websocket, payload):
    await websocket.send(json.dumps({"type": "progress", "payload": payload}, ensure_ascii=False))


async def send_complete(websocket):
    await websocket.send(json.dumps({"type": "complete"}, ensure_ascii=False))
