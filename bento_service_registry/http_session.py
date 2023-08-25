import aiohttp

from fastapi import Depends
from typing import Annotated

from .config import ConfigDependency

__all__ = [
    "get_http_session",
    "HTTPSessionDependency",
]


async def get_http_session(config: ConfigDependency):
    connector = aiohttp.TCPConnector(verify_ssl=config.bento_validate_ssl)
    session = aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=config.contact_timeout),
    )
    try:
        yield session
    finally:
        await session.close()


HTTPSessionDependency = Annotated[aiohttp.ClientSession, Depends(get_http_session)]
