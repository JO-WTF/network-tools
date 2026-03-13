from server.providers.custom import CustomProvider
from server.providers.here import HereProvider
from server.providers.mapbox import MapboxProvider


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


def get_provider(config):
    interface = get_interface_name(config)
    if interface == "here":
        return HereProvider()
    if interface == "mapbox":
        return MapboxProvider()
    return CustomProvider()
