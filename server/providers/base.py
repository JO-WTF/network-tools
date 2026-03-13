from abc import ABC, abstractmethod


class BaseProvider(ABC):
    name = "base"

    @abstractmethod
    async def fetch_token(self, http_client, config):
        raise NotImplementedError

    @abstractmethod
    async def geocode(self, http_client, token, config, address):
        raise NotImplementedError

    @abstractmethod
    async def route(self, http_client, token, config, origin, destination):
        raise NotImplementedError
