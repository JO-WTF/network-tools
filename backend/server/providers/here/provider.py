from server.providers.base.provider import Provider
from server.providers.here.token import fetch_token


class HereProvider(Provider):
    name = "here"

    async def get_auth(self, http_client, config):
        return await fetch_token(http_client, config)
