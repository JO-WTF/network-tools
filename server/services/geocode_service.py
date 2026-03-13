from server.infrastructure.cache import PersistentCache
from server.services.provider_registry import get_interface_name
from server.utils.hash_utils import short_md5

_GEOCODE_PERSISTENT_CACHES = {}


def _get_geocode_persistent_cache(config):
    interface = get_interface_name(config)
    geocode_url = config.get("geocodeUrl") or "default"
    key = f"{interface}_{geocode_url}"
    if key not in _GEOCODE_PERSISTENT_CACHES:
        _GEOCODE_PERSISTENT_CACHES[key] = PersistentCache(f"geocode_{interface}_{short_md5(geocode_url)}")
    return _GEOCODE_PERSISTENT_CACHES[key]


class GeocodeService:
    def __init__(self):
        self.memory_cache = {}

    async def geocode_address(self, provider, http_client, token, config, address):
        cache_key = str(address or "").strip()
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]

        persistent_cache = _get_geocode_persistent_cache(config)
        cached = persistent_cache.get(cache_key)
        if cached is not None:
            self.memory_cache[cache_key] = cached
            return cached

        result = await provider.geocode(http_client, token, config, address)
        self.memory_cache[cache_key] = result
        persistent_cache.set(cache_key, result)
        return result

    def flush(self, config):
        _get_geocode_persistent_cache(config).flush()
