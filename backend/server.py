import asyncio
import json
import hashlib
from pathlib import Path

import aiohttp
import websockets


CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FLUSH_BATCH = 100
WS_MAX_SIZE = 10 * 1024 * 1024


class PersistentCache:
    def __init__(self, name):
        self.path = CACHE_DIR / f"{name}.json"
        self.store = self._load()
        self.pending = 0

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value
        self.pending += 1
        if self.pending >= CACHE_FLUSH_BATCH:
            self.flush()

    def flush(self):
        if self.pending <= 0:
            return
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self.store, f, ensure_ascii=False)
        self.pending = 0


GEOCODE_PERSISTENT_CACHES = {}
ROUTE_PERSISTENT_CACHES = {}


def get_interface_name(config):
    geocode_url = (config.get("geocodeUrl") or "").lower()
    route_url = (config.get("routeUrl") or "").lower()
    combined = f"{geocode_url} {route_url}"
    if "mapbox" in combined:
        return "mapbox"
    if "here" in combined:
        return "here"
    if geocode_url or route_url:
        return "custom"
    return "unknown"


def get_geocode_persistent_cache(config):
    interface = get_interface_name(config)
    geocode_url = config.get("geocodeUrl") or "default"
    key = f"{interface}_{geocode_url}"
    if key not in GEOCODE_PERSISTENT_CACHES:
        digest = hashlib.md5(geocode_url.encode("utf-8")).hexdigest()[:12]
        GEOCODE_PERSISTENT_CACHES[key] = PersistentCache(f"geocode_{interface}_{digest}")
    return GEOCODE_PERSISTENT_CACHES[key]


def get_route_persistent_cache(config):
    interface = get_interface_name(config)
    route_url = config.get("routeUrl") or "default"
    key = f"{interface}_{route_url}"
    if key not in ROUTE_PERSISTENT_CACHES:
        digest = hashlib.md5(route_url.encode("utf-8")).hexdigest()[:12]
        ROUTE_PERSISTENT_CACHES[key] = PersistentCache(f"route_{interface}_{digest}")
    return ROUTE_PERSISTENT_CACHES[key]

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


async def geocode_address(session, token, config, address, geocode_cache, persistent_cache):
    cache_key = str(address or "").strip()
    if cache_key in geocode_cache:
        return geocode_cache[cache_key]
    cached = persistent_cache.get(cache_key)
    if cached is not None:
        geocode_cache[cache_key] = cached
        return cached

    geocode_url = config.get("geocodeUrl")
    if not geocode_url:
        result = {
            "success": False,
            "errorType": "config_error",
            "request": "geocodeUrl",
            "response": "缺少地理编码接口地址",
        }
        geocode_cache[cache_key] = result
        persistent_cache.set(cache_key, result)
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
            persistent_cache.set(cache_key, result)
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
            persistent_cache.set(cache_key, result)
            return result

        result = {
            "success": True,
            "lat": round_coord(lat),
            "lng": round_coord(lng),
        }
        geocode_cache[cache_key] = result
        persistent_cache.set(cache_key, result)
        return result


async def fetch_route(session, token, config, origin, destination, route_cache, persistent_cache):
    cache_key = (origin, destination)
    if cache_key in route_cache:
        return route_cache[cache_key]
    persistent_cache_key = f"{origin}|{destination}"
    cached = persistent_cache.get(persistent_cache_key)
    if cached is not None:
        route_cache[cache_key] = cached
        return cached

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
        persistent_cache.set(persistent_cache_key, result)
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
        lng = round_coord(parts[0])
        lat = round_coord(parts[1])
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
            geocode_persistent_cache = get_geocode_persistent_cache(config)
            route_persistent_cache = get_route_persistent_cache(config)

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
                            session,
                            token,
                            config,
                            origin_value,
                            geocode_cache,
                            geocode_persistent_cache,
                        )
                        destination_result = await geocode_address(
                            session,
                            token,
                            config,
                            destination_value,
                            geocode_cache,
                            geocode_persistent_cache,
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
                                route_persistent_cache,
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
                                route_persistent_cache,
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
                        session,
                        token,
                        config,
                        address,
                        geocode_cache,
                        geocode_persistent_cache,
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

            geocode_persistent_cache.flush()
            route_persistent_cache.flush()

        await websocket.send(json.dumps({"type": "complete"}, ensure_ascii=False))


async def main():
    async with websockets.serve(
        handle_connection,
        "0.0.0.0",
        8765,
        max_size=WS_MAX_SIZE,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
