
async def fetch_token(provider, http_client, config):
    return await provider.fetch_token(http_client, config)
