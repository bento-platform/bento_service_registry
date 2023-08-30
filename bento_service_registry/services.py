import aiohttp
import asyncio
import logging

from bento_lib.types import GA4GHServiceInfo
from datetime import datetime
from fastapi import Depends, status
from json import JSONDecodeError
from typing import Annotated
from urllib.parse import urljoin

from .authz_header import OptionalAuthzHeader, OptionalAuthzHeaderDependency
from .bento_services_json import BentoServicesByKindDependency
from .constants import BENTO_SERVICE_KIND
from .http_session import HTTPSessionDependency
from .logger import LoggerDependency
from .service_info import ServiceInfoDependency
from .types import BentoService


__all__ = [
    "get_service",
    "get_services",
    "ServicesDependency",
]


async def get_service(
    authz_header: OptionalAuthzHeader,
    logger: logging.Logger,
    session: aiohttp.ClientSession,
    service_info: GA4GHServiceInfo,
    service_metadata: BentoService,
) -> dict[str, dict] | None:
    kind = service_metadata["service_kind"]

    # special case: requesting info about the current service. Skip networking / self-connect;
    # instead, return pre-calculated /service-info contents.
    if kind == BENTO_SERVICE_KIND:
        return service_info

    s_url: str = service_metadata["url"]
    service_info_url: str = urljoin(f"{s_url}/", "service-info")

    dt = datetime.now()
    logger.info(f"Contacting {service_info_url}{' with bearer token' if authz_header else ''}")

    service_resp: dict[str, dict] = {}

    try:
        async with session.get(service_info_url, headers=authz_header) as r:
            if r.status != status.HTTP_200_OK:
                r_text = await r.text()
                logger.error(f"Non-200 status code on {kind}: {r.status}  Content: {r_text}")

                # If we have the special case where we got a JWT error from the proxy script, we can safely print out
                # headers for debugging, since the JWT leaked isn't valid anyway.
                if "invalid jwt" in r_text:
                    logger.error(f"Encountered auth error on {kind}; tried to use header: {authz_header}")

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
    authz_header: OptionalAuthzHeaderDependency,
    bento_services_by_kind: BentoServicesByKindDependency,
    http_session: HTTPSessionDependency,
    logger: LoggerDependency,
    service_info: ServiceInfoDependency,
) -> tuple[dict, ...]:
    # noinspection PyTypeChecker
    service_list: list[dict | None] = await asyncio.gather(*[
        get_service(authz_header, logger, http_session, service_info, s)
        for s in bento_services_by_kind.values()
    ])
    return tuple(s for s in service_list if s is not None)


ServicesDependency = Annotated[tuple[dict, ...], Depends(get_services)]
