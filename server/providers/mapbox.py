from server.utils.coords import round_coord
from server.utils.json_utils import dump_json

from .base import BaseProvider


class MapboxProvider(BaseProvider):
    name = "mapbox"

    async def fetch_token(self, http_client, config):
        token_url = config.get("tokenUrl")
        if not token_url:
            return ""

        payload = {
            "appId": config.get("appId", ""),
            "credential": config.get("credential", ""),
        }
        status, data = await http_client.post_json(token_url, payload=payload)
        if status != 200:
            return ""
        state = data.get("status", {})
        if state.get("statusCode") != "SUCCESS":
            return ""
        return data.get("result", "")

    async def geocode(self, http_client, token, config, address):
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

        payload = {"address": str(address or "").strip(), "language": "en", "coordType": "wgs84"}
        status, data = await http_client.post_json(geocode_url, payload=payload, headers=headers)
        if status != 200 or data.get("status") != "OK":
            return {
                "success": False,
                "errorType": "network_error",
                "request": geocode_url,
                "response": dump_json(data),
            }

        location = data.get("result", {}).get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")
        if lat is None or lng is None:
            return {
                "success": False,
                "errorType": "no_result",
                "request": geocode_url,
                "response": dump_json(data),
            }
        return {"success": True, "lat": round_coord(lat), "lng": round_coord(lng)}

    async def route(self, http_client, token, config, origin, destination):
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
            "coordType": "wgs84",
            "countryArea": "china",
        }
        status, data = await http_client.post_json(route_url, payload=payload, headers=headers)
        if status != 200:
            return {
                "success": False,
                "errorType": "network_error",
                "request": route_url,
                "response": dump_json(data),
            }

        distance_value = (data.get("distance") or {}).get("value")
        duration_value = (data.get("duration") or {}).get("value")
        if distance_value is None or duration_value is None:
            return {
                "success": False,
                "errorType": "no_result",
                "request": route_url,
                "response": dump_json(data),
            }

        return {
            "success": True,
            "distanceKm": round(distance_value / 1000, 2),
            "durationMin": round(duration_value / 60),
        }
