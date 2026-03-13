from server.infrastructure.http_client import HttpClient
from server.infrastructure.logger import info
from server.services.auth_service import fetch_token
from server.services.geocode_service import GeocodeService
from server.services.provider_registry import get_provider
from server.services.route_service import RouteService
from server.utils.coords import format_coord_pair, parse_coordinate, round_coord
from server.websocket.parser import parse_message
from server.websocket.responder import send_complete, send_progress


async def handle_connection(websocket):
    info("client connected:", websocket.remote_address)

    async for message in websocket:
        info("recv:", message)
        payload, parse_error = parse_message(message)
        if parse_error:
            await send_progress(websocket, parse_error)
            continue

        if payload.get("type") != "start":
            continue

        payload_data = payload.get("payload", {})
        mode = payload_data.get("mode", "geocode")
        route_input_mode = payload_data.get("routeInputMode", "address")
        config = payload_data.get("config", {})
        addresses = payload_data.get("addresses", [])
        routes = payload_data.get("routes", [])

        provider = get_provider(config)
        geocode_service = GeocodeService()
        route_service = RouteService()

        async with HttpClient() as http_client:
            token = await fetch_token(provider, http_client, config)
            if not token:
                items = routes if mode == "route" else addresses
                for index, item in enumerate(items, start=1):
                    address = item.get("origin") if mode == "route" else item
                    await send_progress(
                        websocket,
                        {
                            "address": address,
                            "processed": index,
                            "success": False,
                            "errorType": "auth_error",
                            "request": config.get("tokenUrl", "token"),
                            "response": "无法获取 Token",
                            "index": index - 1,
                        },
                    )
                await send_complete(websocket)
                continue

            if mode == "route":
                for index, route in enumerate(routes, start=1):
                    origin_value = route.get("origin")
                    destination_value = route.get("destination")
                    origin_coords = None
                    destination_coords = None

                    if route_input_mode == "address":
                        origin_result = await geocode_service.geocode_address(
                            provider, http_client, token, config, origin_value
                        )
                        destination_result = await geocode_service.geocode_address(
                            provider, http_client, token, config, destination_value
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
                            failure = origin_result if not origin_result.get("success") else destination_result
                            result = {
                                "success": False,
                                "errorType": failure.get("errorType", "no_result"),
                                "request": failure.get("request", "geocode"),
                                "response": failure.get("response", "地址无法转换为经纬度"),
                            }
                        else:
                            origin_value = format_coord_pair(origin_coords[0], origin_coords[1])
                            destination_value = format_coord_pair(destination_coords[0], destination_coords[1])
                            result = await route_service.fetch_route(
                                provider, http_client, token, config, origin_value, destination_value
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
                            destination_value = format_coord_pair(destination_coords[0], destination_coords[1])
                            result = await route_service.fetch_route(
                                provider, http_client, token, config, origin_value, destination_value
                            )

                    await send_progress(
                        websocket,
                        {
                            "processed": index,
                            "success": result.get("success"),
                            "distanceKm": result.get("distanceKm"),
                            "durationMin": result.get("durationMin"),
                            "errorType": result.get("errorType"),
                            "request": result.get("request"),
                            "response": result.get("response"),
                            "originLat": origin_coords[0] if origin_coords else None,
                            "originLng": origin_coords[1] if origin_coords else None,
                            "destinationLat": destination_coords[0] if destination_coords else None,
                            "destinationLng": destination_coords[1] if destination_coords else None,
                            "index": index - 1,
                        },
                    )
            else:
                for index, address in enumerate(addresses, start=1):
                    result = await geocode_service.geocode_address(provider, http_client, token, config, address)
                    await send_progress(
                        websocket,
                        {
                            "address": address,
                            "processed": index,
                            "success": result.get("success"),
                            "lat": result.get("lat"),
                            "lng": result.get("lng"),
                            "errorType": result.get("errorType"),
                            "request": result.get("request"),
                            "response": result.get("response"),
                        },
                    )

            geocode_service.flush(config)
            route_service.flush(config)

        await send_complete(websocket)
