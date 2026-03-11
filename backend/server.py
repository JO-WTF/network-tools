import asyncio
import json

import aiohttp
import websockets


def round_coord(value):
    if value is None:
        return None
    return round(float(value), 6)


def format_coord_pair(lat, lng):
    return f"{round_coord(lat):.6f},{round_coord(lng):.6f}"


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


async def geocode_address(session, token, config, address, geocode_cache):
    cache_key = str(address or "").strip()
    if cache_key in geocode_cache:
        return geocode_cache[cache_key]

    geocode_url = config.get("geocodeUrl")
    if not geocode_url:
        result = {
            "success": False,
            "errorType": "config_error",
            "request": "geocodeUrl",
            "response": "缺少地理编码接口地址",
        }
        geocode_cache[cache_key] = result
        return result

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token

    payload = {
        "address": cache_key,
        "language": "en",
        "coordType": "wgs84",
    }

    async with session.post(geocode_url, json=payload, headers=headers, ssl=False) as response:
        data = await response.json()
        if response.status != 200 or data.get("status") != "OK":
            result = {
                "success": False,
                "errorType": "network_error",
                "request": geocode_url,
                "response": json.dumps(data, ensure_ascii=False),
            }
            geocode_cache[cache_key] = result
            return result

        location = data.get("result", {}).get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")
        if lat is None or lng is None:
            result = {
                "success": False,
                "errorType": "no_result",
                "request": geocode_url,
                "response": json.dumps(data, ensure_ascii=False),
            }
            geocode_cache[cache_key] = result
            return result

        result = {
            "success": True,
            "lat": round_coord(lat),
            "lng": round_coord(lng),
        }
        geocode_cache[cache_key] = result
        return result


async def fetch_route(session, token, config, origin, destination, route_cache):
    cache_key = (origin, destination)
    if cache_key in route_cache:
        return route_cache[cache_key]

    route_url = config.get("routeUrl")
    if not route_url:
        result = {
            "success": False,
            "errorType": "config_error",
            "request": "routeUrl",
            "response": "缺少导航接口地址",
        }
        route_cache[cache_key] = result
        return result

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token

    payload = {
        "origin": origin,
        "destination": destination,
        "language": "zh",
        "coordType": "wgs84",
        "countryArea": "china",
    }

    async with session.post(route_url, json=payload, headers=headers, ssl=False) as response:
        data = await response.json()
        if response.status != 200:
            result = {
                "success": False,
                "errorType": "network_error",
                "request": route_url,
                "response": json.dumps(data, ensure_ascii=False),
            }
            route_cache[cache_key] = result
            return result

        distance_value = (data.get("distance") or {}).get("value")
        duration_value = (data.get("duration") or {}).get("value")
        if distance_value is None or duration_value is None:
            result = {
                "success": False,
                "errorType": "no_result",
                "request": route_url,
                "response": json.dumps(data, ensure_ascii=False),
            }
            route_cache[cache_key] = result
            return result

        result = {
            "success": True,
            "distanceKm": round(distance_value / 1000, 2),
            "durationMin": round(duration_value / 60),
        }
        route_cache[cache_key] = result
        return result


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
        lat = round_coord(parts[0])
        lng = round_coord(parts[1])
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
                    },
                    ensure_ascii=False,
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
            geocode_cache = {}
            route_cache = {}

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
                            },
                            ensure_ascii=False,
                        )
                    )
                await websocket.send(json.dumps({"type": "complete"}, ensure_ascii=False))
                continue

            if mode == "route":
                for index, route in enumerate(routes, start=1):
                    origin_value = route.get("origin")
                    destination_value = route.get("destination")
                    origin_coords = None
                    destination_coords = None

                    if route_input_mode == "address":
                        origin_result = await geocode_address(
                            session, token, config, origin_value, geocode_cache
                        )
                        destination_result = await geocode_address(
                            session, token, config, destination_value, geocode_cache
                        )

                        if origin_result.get("success"):
                            origin_coords = (
                                round_coord(origin_result.get("lat")),
                                round_coord(origin_result.get("lng")),
                            )
                        if destination_result.get("success"):
                            destination_coords = (
                                round_coord(destination_result.get("lat")),
                                round_coord(destination_result.get("lng")),
                            )

                        if not origin_result.get("success") or not destination_result.get("success"):
                            failure = (
                                origin_result
                                if not origin_result.get("success")
                                else destination_result
                            )
                            result = {
                                "success": False,
                                "errorType": failure.get("errorType", "no_result"),
                                "request": failure.get("request", "geocode"),
                                "response": failure.get("response", "地址无法转换为经纬度"),
                            }
                        else:
                            origin_value = format_coord_pair(origin_coords[0], origin_coords[1])
                            destination_value = format_coord_pair(
                                destination_coords[0], destination_coords[1]
                            )
                            result = await fetch_route(
                                session,
                                token,
                                config,
                                origin_value,
                                destination_value,
                                route_cache,
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
                            origin_value = format_coord_pair(origin_coords[0], origin_coords[1])
                            destination_value = format_coord_pair(
                                destination_coords[0], destination_coords[1]
                            )
                            result = await fetch_route(
                                session,
                                token,
                                config,
                                origin_value,
                                destination_value,
                                route_cache,
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
                                    "destinationLat": (
                                        destination_coords[0] if destination_coords else None
                                    ),
                                    "destinationLng": (
                                        destination_coords[1] if destination_coords else None
                                    ),
                                    "index": index - 1,
                                },
                            },
                            ensure_ascii=False,
                        )
                    )
            else:
                for index, address in enumerate(addresses, start=1):
                    result = await geocode_address(
                        session, token, config, address, geocode_cache
                    )
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

        await websocket.send(json.dumps({"type": "complete"}, ensure_ascii=False))


async def main():
    async with websockets.serve(handle_connection, "0.0.0.0", 8765):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
