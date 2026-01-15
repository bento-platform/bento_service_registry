import aiohttp
import asyncio
import structlog.stdlib

from aiohttp import ClientSession
from bento_lib.service_info.types import GA4GHServiceInfo
from datetime import datetime
from fastapi import Depends, status
from functools import lru_cache
from json import JSONDecodeError
from typing import Annotated, Awaitable
from urllib.parse import urljoin

from .authz_header import OptionalHeaders, OptionalAuthzHeaderDependency
from .bento_services_json import BentoServicesByKind, BentoServicesByKindDependency
from .config import Config, ConfigDependency
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
    def __init__(self, config: Config, logger: structlog.stdlib.BoundLogger):
        self._config: Config = config
        self._co: Awaitable[list[dict | None]] | None = None
        self._logger: structlog.stdlib.BoundLogger = logger
        self._cache: dict[str, tuple[datetime, GA4GHServiceInfo]] = {}

    async def get_service(
        self,
        authz_header: OptionalAuthzHeaderDependency,
        http_session: HTTPSessionDependency,
        service_info: ServiceInfoDependency,
        service_metadata: BentoService,
    ) -> GA4GHServiceInfo | None:
        kind = service_metadata["service_kind"]
        s_url: str = service_metadata["url"]

        # special case: requesting info about the current service. Skip networking / self-connect;
        # instead, return pre-calculated /service-info contents.
        if kind == BENTO_SERVICE_KIND:
            return GA4GHServiceInfo(**service_info, url=s_url)

        service_info_url: str = urljoin(f"{s_url}/", "service-info")
        logger = self._logger.bind(service_kind=kind, service_info_url=service_info_url)

        dt = datetime.now()

        if service_info_url in self._cache:
            entry_dt, entry = self._cache[service_info_url]
            if (entry_age := (dt - entry_dt).total_seconds()) > self._config.cache_ttl:
                del self._cache[service_info_url]
            else:
                await logger.adebug("found service info in cache", cache_age=entry_age)
                return entry

        await logger.ainfo("contacting service info", with_bearer_token=bool(authz_header))

        service_resp: dict | None = None

        try:
            async with http_session.get(service_info_url, headers=authz_header) as r:
                if r.status != status.HTTP_200_OK:
                    r_text = await r.text()
                    await logger.aerror("service info fetch non-200 status code", status=r.status, body=r_text)

                    # If we have the special case where we got a JWT error from the proxy script, we can safely print
                    # out headers for debugging, since the JWT leaked isn't valid anyway.
                    if "invalid jwt" in r_text:
                        await logger.aerror("service info fetch encountered auth error", authz_header=authz_header)

                    return None

                try:
                    service_resp = {**(await r.json()), "url": s_url}
                    res_dt = datetime.now()
                    self._cache[service_info_url] = (res_dt, GA4GHServiceInfo(**service_resp))
                    await logger.adebug("service info fetch complete", time_taken=(res_dt - dt).total_seconds())
                except (JSONDecodeError, aiohttp.ContentTypeError, TypeError) as e:
                    # JSONDecodeError can happen if the JSON is invalid
                    # ContentTypeError can happen if the Content-Type is not application/json
                    # TypeError can happen if None is received
                    await logger.aexception(
                        "service info fetch invalid response",
                        exc_info=e,
                        body=await r.text(),
                        time_taken=(datetime.now() - dt).total_seconds(),
                    )

        except asyncio.TimeoutError:
            await logger.aerror("service info fetch timeout")

        except aiohttp.ClientConnectionError as e:
            await logger.aexception("service info fetch connection error", exc_info=e)

        return service_resp

    async def get_services(
        self,
        authz_header: OptionalHeaders,
        bento_services_by_kind: BentoServicesByKind,
        http_session: ClientSession,
        service_info: GA4GHServiceInfo,
    ) -> tuple[dict, ...]:
        if not self._co:
            self._co = asyncio.gather(
                *(
                    self.get_service(authz_header, http_session, service_info, s)
                    for s in bento_services_by_kind.values()
                )
            )

        service_list: list[dict | None] = await self._co
        self._co = None

        return tuple(s for s in service_list if s is not None)


@lru_cache
def get_service_manager(
    config: ConfigDependency,
    logger: LoggerDependency,
):
    return ServiceManager(config, logger)


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
