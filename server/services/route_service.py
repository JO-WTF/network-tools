from server.infrastructure.cache import PersistentCache
from server.services.provider_registry import get_interface_name
from server.utils.hash_utils import short_md5

_ROUTE_PERSISTENT_CACHES = {}


def _get_route_persistent_cache(config):
    interface = get_interface_name(config)
    route_url = config.get("routeUrl") or "default"
    key = f"{interface}_{route_url}"
    if key not in _ROUTE_PERSISTENT_CACHES:
        _ROUTE_PERSISTENT_CACHES[key] = PersistentCache(f"route_{interface}_{short_md5(route_url)}")
    return _ROUTE_PERSISTENT_CACHES[key]


class RouteService:
    def __init__(self):
        self.memory_cache = {}

    async def fetch_route(self, provider, http_client, token, config, origin, destination):
        cache_key = (origin, destination)
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]

        persistent_cache = _get_route_persistent_cache(config)
        persistent_key = f"{origin}|{destination}"
        cached = persistent_cache.get(persistent_key)
        if cached is not None:
            self.memory_cache[cache_key] = cached
            return cached

        result = await provider.route(http_client, token, config, origin, destination)
        self.memory_cache[cache_key] = result
        if result.get("success"):
            persistent_cache.set(persistent_key, result)
        return result

    def flush(self, config):
        _get_route_persistent_cache(config).flush()
