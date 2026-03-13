import aiohttp


class HttpClient:
    def __init__(self):
        self._session = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session:
            await self._session.close()

    async def post_json(self, url, *, payload=None, headers=None):
        async with self._session.post(url, json=payload, headers=headers, ssl=False) as response:
            data = await response.json()
            return response.status, data
