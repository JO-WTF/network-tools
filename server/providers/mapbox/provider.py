from server.providers.base.provider import Provider
from server.providers.mapbox.token import fetch_token


class MapboxProvider(Provider):
    name = "mapbox"

    async def get_auth(self, http_client, config):
        return await fetch_token(http_client, config)
