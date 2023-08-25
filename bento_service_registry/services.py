import aiohttp
import asyncio
import logging

from datetime import datetime
from fastapi import Depends, Request, status
from json import JSONDecodeError
from typing import Annotated
from urllib.parse import urljoin

from .bento_services_json import BentoServicesByKind, BentoServicesByKindDependency
from .config import Config, ConfigDependency
from .constants import BENTO_SERVICE_KIND
from .http_session import HTTPSessionDependency
from .logger import LoggerDependency
from .service_info import get_service_info
from .types import BentoService


__all__ = [
    "get_service_url",
    "get_service",
    "get_services",
    "ServicesDependency",
]


def get_service_url(services_by_kind: BentoServicesByKind, service_kind: str) -> str:
    return services_by_kind[service_kind]["url"]


async def get_service(
    bento_services_by_kind: BentoServicesByKind,
    config: Config,
    logger: logging.Logger,
    request: Request,
    session: aiohttp.ClientSession,
    service_metadata: BentoService,
) -> dict[str, dict] | None:
    kind = service_metadata["service_kind"]

    # special case: requesting info about the current service. Skip networking / self-connect.
    if kind == BENTO_SERVICE_KIND:
        return await get_service_info(bento_services_by_kind, config, logger)

    s_url: str = service_metadata["url"]
    service_info_url: str = urljoin(f"{s_url}/", "service-info")

    # Optional Authorization HTTP header to forward to nested requests
    auth_header: str = request.headers.get("Authorization", "")
    headers = {"Authorization": auth_header} if auth_header else {}

    dt = datetime.now()
    logger.info(f"Contacting {service_info_url}{' with bearer token' if auth_header else ''}")

    service_resp: dict[str, dict] = {}

    try:
        async with session.get(service_info_url, headers=headers) as r:
            if r.status != status.HTTP_200_OK:
                r_text = await r.text()
                logger.error(f"Non-200 status code on {kind}: {r.status}  Content: {r_text}")

                # If we have the special case where we got a JWT error from the proxy script, we can safely print out
                # headers for debugging, since the JWT leaked isn't valid anyway.
                if "invalid jwt" in r_text:
                    logger.error(f"Encountered auth error on {kind}; tried to use header: {auth_header}")

                return None

            try:
                service_resp[kind] = {**(await r.json()), "url": s_url}
            except (JSONDecodeError, aiohttp.ContentTypeError, TypeError) as e:
                # JSONDecodeError can happen if the JSON is invalid
                # ContentTypeError can happen if the Content-Type is not application/json
                # TypeError can happen if None is received
                logger.error(f"Encountered invalid response ({str(e)}) from {service_info_url}: {await r.text()}")

            logger.info(f"{service_info_url}: Took {(datetime.now() - dt).total_seconds():.1f}s")

    except asyncio.TimeoutError:
        logger.error(f"Encountered timeout with {service_info_url}")

    except aiohttp.ClientConnectionError as e:
        logger.error(f"Encountered connection error with {service_info_url}: {str(e)}")

    return service_resp.get(kind)


async def get_services(
    bento_services_by_kind: BentoServicesByKindDependency,
    config: ConfigDependency,
    http_session: HTTPSessionDependency,
    logger: LoggerDependency,
    request: Request,
) -> tuple[dict, ...]:
    # noinspection PyTypeChecker
    service_list: list[dict | None] = await asyncio.gather(*[
        get_service(bento_services_by_kind, config, logger, request, http_session, s)
        for s in bento_services_by_kind.values()
    ])
    return tuple(s for s in service_list if s is not None)


ServicesDependency = Annotated[tuple[dict, ...], Depends(get_services)]
