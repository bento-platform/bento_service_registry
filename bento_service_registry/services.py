import aiohttp
import asyncio
import logging

from aiohttp import ClientSession
from bento_lib.service_info.types import GA4GHServiceInfo
from datetime import datetime
from fastapi import Depends, status
from functools import lru_cache
from json import JSONDecodeError
from typing import Annotated, Awaitable
from urllib.parse import urljoin

from .authz_header import OptionalAuthzHeader, OptionalAuthzHeaderDependency
from .bento_services_json import BentoServicesByKind, BentoServicesByKindDependency
from .constants import BENTO_SERVICE_KIND
from .http_session import HTTPSessionDependency
from .logger import LoggerDependency
from .service_info import ServiceInfoDependency
from .types import BentoService


__all__ = [
    "get_service_manager",
    "ServiceManagerDependency",
    "get_services",
    "ServicesDependency",
]


class ServiceManager:
    def __init__(self, logger: logging.Logger):
        self._co: Awaitable[list[dict | None]] | None = None
        self._logger = logger

    async def get_service(
        self,
        authz_header: OptionalAuthzHeaderDependency,
        http_session: HTTPSessionDependency,
        service_info: ServiceInfoDependency,
        service_metadata: BentoService,
    ) -> dict | None:
        kind = service_metadata["service_kind"]
        s_url: str = service_metadata["url"]

        # special case: requesting info about the current service. Skip networking / self-connect;
        # instead, return pre-calculated /service-info contents.
        if kind == BENTO_SERVICE_KIND:
            return {**service_info, "url": s_url}

        service_info_url: str = urljoin(f"{s_url}/", "service-info")

        dt = datetime.now()
        self._logger.info(f"Contacting {service_info_url}{' with bearer token' if authz_header else ''}")

        service_resp: dict | None = None

        try:
            async with http_session.get(service_info_url, headers=authz_header) as r:
                if r.status != status.HTTP_200_OK:
                    r_text = await r.text()
                    self._logger.error(f"Non-200 status code on {kind}: {r.status}  Content: {r_text}")

                    # If we have the special case where we got a JWT error from the proxy script, we can safely print
                    # out headers for debugging, since the JWT leaked isn't valid anyway.
                    if "invalid jwt" in r_text:
                        self._logger.error(f"Encountered auth error on {kind}; tried to use header: {authz_header}")

                    return None

                try:
                    service_resp = {**(await r.json()), "url": s_url}
                    self._logger.info(f"{service_info_url}: Took {(datetime.now() - dt).total_seconds():.1f}s")
                except (JSONDecodeError, aiohttp.ContentTypeError, TypeError) as e:
                    # JSONDecodeError can happen if the JSON is invalid
                    # ContentTypeError can happen if the Content-Type is not application/json
                    # TypeError can happen if None is received
                    self._logger.error(
                        f"{service_info_url}: Encountered invalid response ({str(e)}) - {await r.text()} "
                        f"(Took {(datetime.now() - dt).total_seconds():.1f}s)")

        except asyncio.TimeoutError:
            self._logger.error(f"Encountered timeout with {service_info_url}")

        except aiohttp.ClientConnectionError as e:
            self._logger.error(f"Encountered connection error with {service_info_url}: {str(e)}")

        return service_resp

    async def get_services(
        self,
        authz_header: OptionalAuthzHeader,
        bento_services_by_kind: BentoServicesByKind,
        http_session: ClientSession,
        service_info: GA4GHServiceInfo,
    ) -> tuple[dict, ...]:
        if not self._co:
            self._co = asyncio.gather(*[
                self.get_service(authz_header, http_session, service_info, s)
                for s in bento_services_by_kind.values()
            ])

        service_list: list[dict | None] = await self._co
        self._co = None

        return tuple(s for s in service_list if s is not None)


@lru_cache
def get_service_manager(
    logger: LoggerDependency,
):
    return ServiceManager(logger)


ServiceManagerDependency = Annotated[ServiceManager, Depends(get_service_manager)]


async def get_services(
    authz_header: OptionalAuthzHeaderDependency,
    bento_services_by_kind: BentoServicesByKindDependency,
    http_session: HTTPSessionDependency,
    service_info: ServiceInfoDependency,
    service_manager: ServiceManagerDependency,
) -> tuple[dict, ...]:
    # noinspection PyTypeChecker
    return await service_manager.get_services(
        authz_header,
        bento_services_by_kind,
        http_session,
        service_info,
    )


ServicesDependency = Annotated[tuple[dict, ...], Depends(get_services)]
