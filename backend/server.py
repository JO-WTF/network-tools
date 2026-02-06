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


async def fetch_route(session, token, config, origin, destination):
    route_url = config.get("routeUrl")
    if not route_url:
        return {
            "success": False,
            "errorType": "config_error",
            "request": "routeUrl",
            "response": "缺少导航接口地址",
        }
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token
    payload = {
        "origin": origin,
        "destination": destination,
        "language": "zh",
        "coordType": "gcj02ll",
        "countryArea": "china",
    }
    async with session.post(route_url, json=payload, headers=headers, ssl=False) as response:
        data = await response.json()
        if response.status != 200:
            return {
                "success": False,
                "errorType": "network_error",
                "request": route_url,
                "response": json.dumps(data, ensure_ascii=False),
            }
        distance_value = (data.get("distance") or {}).get("value")
        duration_value = (data.get("duration") or {}).get("value")
        if distance_value is None or duration_value is None:
            return {
                "success": False,
                "errorType": "no_result",
                "request": route_url,
                "response": json.dumps(data, ensure_ascii=False),
            }
        return {
            "success": True,
            "distanceKm": round(distance_value / 1000, 2),
            "durationMin": round(duration_value / 60),
        }


def parse_coordinate(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    delimiter = "," if "," in raw else "，" if "，" in raw else None
    if not delimiter:
        return None
    parts = [item.strip() for item in raw.split(delimiter)]
    if len(parts) < 2:
        return None
    try:
        lat = float(parts[0])
        lng = float(parts[1])
    except ValueError:
        return None
    return lat, lng


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

        payload_data = payload.get("payload", {})
        mode = payload_data.get("mode", "geocode")
        route_input_mode = payload_data.get("routeInputMode", "address")
        config = payload_data.get("config", {})
        addresses = payload_data.get("addresses", [])
        routes = payload_data.get("routes", [])
        async with aiohttp.ClientSession() as session:
            token = await fetch_token(session, config)
            if not token:
                items = routes if mode == "route" else addresses
                for index, item in enumerate(items, start=1):
                    address = item.get("origin") if mode == "route" else item
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
                                    "index": index - 1,
                                },
                            }
                        )
                    )
                await websocket.send(json.dumps({"type": "complete"}))
                continue

            if mode == "route":
                for index, route in enumerate(routes, start=1):
                    origin_value = route.get("origin")
                    destination_value = route.get("destination")
                    origin_coords = None
                    destination_coords = None
                    if route_input_mode == "address":
                        origin_result = await geocode_address(session, token, config, origin_value)
                        destination_result = await geocode_address(
                            session, token, config, destination_value
                        )
                        if not origin_result.get("success") or not destination_result.get("success"):
                            failure = (
                                origin_result if not origin_result.get("success") else destination_result
                            )
                            result = {
                                "success": False,
                                "errorType": failure.get("errorType", "no_result"),
                                "request": failure.get("request", "geocode"),
                                "response": failure.get("response", "地址无法转换为经纬度"),
                            }
                        else:
                            origin_coords = (
                                origin_result.get("lat"),
                                origin_result.get("lng"),
                            )
                            destination_coords = (
                                destination_result.get("lat"),
                                destination_result.get("lng"),
                            )
                            origin_value = f"{origin_coords[0]},{origin_coords[1]}"
                            destination_value = f"{destination_coords[0]},{destination_coords[1]}"
                            result = await fetch_route(
                                session, token, config, origin_value, destination_value
                            )
                    else:
                        origin_coords = parse_coordinate(origin_value)
                        destination_coords = parse_coordinate(destination_value)
                        if not origin_coords or not destination_coords:
                            result = {
                                "success": False,
                                "errorType": "invalid",
                                "request": "coordinate",
                                "response": "坐标格式错误",
                            }
                        else:
                            origin_value = f"{origin_coords[0]},{origin_coords[1]}"
                            destination_value = f"{destination_coords[0]},{destination_coords[1]}"
                            result = await fetch_route(
                                session, token, config, origin_value, destination_value
                            )
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "progress",
                                "payload": {
                                    "processed": index,
                                    "success": result.get("success"),
                                    "distanceKm": result.get("distanceKm"),
                                    "durationMin": result.get("durationMin"),
                                    "errorType": result.get("errorType"),
                                    "request": result.get("request"),
                                    "response": result.get("response"),
                                    "originLat": origin_coords[0] if origin_coords else None,
                                    "originLng": origin_coords[1] if origin_coords else None,
                                    "destinationLat": destination_coords[0]
                                    if destination_coords
                                    else None,
                                    "destinationLng": destination_coords[1]
                                    if destination_coords
                                    else None,
                                    "index": index - 1,
                                },
                            },
                            ensure_ascii=False,
                        )
                    )
            else:
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
