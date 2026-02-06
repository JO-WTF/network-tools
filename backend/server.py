import asyncio
import json

import aiohttp
import websockets


async def fetch_token(session, config):
    token_url = config.get("tokenUrl")
    if not token_url:
        return ""
    payload = {
        "appId": config.get("appId", ""),
        "credential": config.get("credential", ""),
    }
    print(payload)
    async with session.post(token_url, json=payload, ssl=False) as response:
        data = await response.json()
        if response.status != 200:
            return ""
        print(data)
        status = data.get("status", {})
        if status.get("statusCode") != "SUCCESS":
            return ""
        return data.get("result", "")


async def geocode_address(session, token, config, address):
    geocode_url = config.get("geocodeUrl")
    if not geocode_url:
        return {
            "success": False,
            "errorType": "config_error",
            "request": "geocodeUrl",
            "response": "缺少地理编码接口地址",
        }
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token
    payload = {"address": address, "language": "en", "coordType": "wgs84"}
    async with session.post(geocode_url, json=payload, headers=headers, ssl=False) as response:
        data = await response.json()
        if response.status != 200 or data.get("status") != "OK":
            return {
                "success": False,
                "errorType": "network_error",
                "request": geocode_url,
                "response": json.dumps(data, ensure_ascii=False),
            }
        location = data.get("result", {}).get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")
        if lat is None or lng is None:
            return {
                "success": False,
                "errorType": "no_result",
                "request": geocode_url,
                "response": json.dumps(data, ensure_ascii=False),
            }
        return {"success": True, "lat": lat, "lng": lng}


async def handle_connection(websocket):
    print("client connected:", websocket.remote_address)
    async for message in websocket:
        print("recv:", message)
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            await websocket.send(
                json.dumps(
                    {
                        "type": "progress",
                        "payload": {
                            "success": False,
                            "errorType": "parse_error",
                            "request": "websocket",
                            "response": "无法解析请求内容",
                        },
                    }
                )
            )
            continue

        if payload.get("type") != "start":
            continue

        config = payload.get("payload", {}).get("config", {})
        addresses = payload.get("payload", {}).get("addresses", [])
        async with aiohttp.ClientSession() as session:
            token = await fetch_token(session, config)
            if not token:
                for index, address in enumerate(addresses, start=1):
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "progress",
                                "payload": {
                                    "address": address,
                                    "processed": index,
                                    "success": False,
                                    "errorType": "auth_error",
                                    "request": config.get("tokenUrl", "token"),
                                    "response": "无法获取 Token",
                                },
                            }
                        )
                    )
                await websocket.send(json.dumps({"type": "complete"}))
                continue

            for index, address in enumerate(addresses, start=1):
                result = await geocode_address(session, token, config, address)
                await websocket.send(
                    json.dumps(
                        {
                            "type": "progress",
                            "payload": {
                                "address": address,
                                "processed": index,
                                "success": result.get("success"),
                                "lat": result.get("lat"),
                                "lng": result.get("lng"),
                                "errorType": result.get("errorType"),
                                "request": result.get("request"),
                                "response": result.get("response"),
                            },
                        },
                        ensure_ascii=False,
                    )
                )

        await websocket.send(json.dumps({"type": "complete"}))


async def main():
    async with websockets.serve(handle_connection, "0.0.0.0", 8765):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
