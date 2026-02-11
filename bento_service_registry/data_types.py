import aiohttp
import asyncio
import itertools
import structlog.stdlib

from datetime import datetime
from fastapi import Depends, status
from functools import cache
from pydantic import ValidationError
from typing import Annotated
from urllib.parse import urlencode, urljoin

from .authz_header import OptionalHeaders, OptionalAuthzHeaderDependency
from .http_session import HTTPSessionDependency
from .logger import LoggerDependency
from .models import DataTypeWithServiceURL
from .services import ServicesDependency
from .utils import right_slash_normalize_url, authz_header_digest

__all__ = [
    "DataTypesTuple",
    "get_data_types",
    "DataTypesDependency",
]


DataTypesTuple = tuple[DataTypeWithServiceURL, ...]


class DataTypeManager:
    def __init__(self, logger: structlog.stdlib.BoundLogger):
        self.logger = logger

        # cache
        #  - expiry in seconds
        self._cache_expiry: float = 3600.0
        self._data_services: int | None = None
        #  - dict of (project, dataset, hash of auth header): (fetch time, data types)
        self._data_types: dict[tuple[str | None, str | None, str], tuple[datetime, DataTypesTuple]] = {}

    @staticmethod
    def build_scope_query_params(project: str | None, dataset: str | None) -> str:
        qp = {}
        if project:
            qp["project"] = project
        if dataset:
            qp["dataset"] = dataset
        return f"?{urlencode(qp)}" if qp else ""

    async def get_data_types_from_service(
        self,
        authz_header: OptionalHeaders,
        http_session: aiohttp.ClientSession,
        service: dict,
        project: str | None,
        dataset: str | None,
    ) -> tuple[DataTypesTuple, bool]:
        service_url: str | None = service.get("url")

        if service_url is None:
            await self.logger.aerror("encountered service with missing URL", service=service)
            return (), False

        service_url_norm: str = right_slash_normalize_url(service_url)
        data_types_url = urljoin(service_url_norm, "data-types") + self.build_scope_query_params(project, dataset)

        logger = self.logger.bind(data_types_url=data_types_url)

        try:
            async with http_session.get(data_types_url, headers=authz_header) as res:
                data = await res.json()
                if res.status != status.HTTP_200_OK:
                    await logger.aerror("got non-200 response from data type service", status=res.status, body=data)
                    return (), False
        except asyncio.TimeoutError:
            await logger.aerror("service data type fetch timeout error")
            return (), False
        except aiohttp.ClientConnectionError as e:
            await logger.aexception("service data type fetch connection error", exc_info=e)
            return (), False

        dts: list[DataTypeWithServiceURL] = []

        for dt in data:
            try:
                dts.append(DataTypeWithServiceURL.model_validate({**dt, "service_base_url": service_url_norm}))
            except ValidationError as err:
                await logger.aerror("skipping recieved malformatted data type", data_type=dt, exc_info=err)
                continue

        return tuple(dts), True

    async def get_data_types(
        self,
        authz_header: OptionalHeaders,
        http_session: aiohttp.ClientSession,
        services_tuple: tuple[dict, ...],
        project: str | None,
        dataset: str | None,
    ) -> DataTypesTuple:
        now = datetime.now()
        scope = (project, dataset)

        data_services = [s for s in services_tuple if s.get("bento", {}).get("dataService", False)]
        n_data_services = len(data_services)

        logger = self.logger.bind(n_data_services=n_data_services, scope=scope)

        if self._data_services is not None and n_data_services != self._data_services:
            self._data_types.clear()
            self._data_services = n_data_services

        # If we have the data for the specified scope in cache, return it instead of doing a lot of fetching effort
        #  - we need to use a SECURE hash for the auth header, to avoid hash collision attacks getting counts where the
        #    accessor shouldn't have permission to!
        #  - we need to cache based on auth header in the first place because data types include entity counts
        cache_key = (scope[0], scope[1], authz_header_digest(authz_header))

        if (dts := self._data_types.get(cache_key)) is not None and (now - dts[0]).total_seconds() < self._cache_expiry:
            await logger.adebug(
                "returning data types from cache",
                time_taken=(datetime.now() - now).total_seconds(),
                n_data_types=len(dts[1]),
            )
            return dts[1]

        # Otherwise, contact data services to fetch data types. If all return a successful response, cache it.

        data_type_results: list[tuple[DataTypesTuple, bool]] = await asyncio.gather(
            *(self.get_data_types_from_service(authz_header, http_session, s, project, dataset) for s in data_services)
        )

        # if at least one service returned something invalid, we can't store the cached results.
        at_least_one_invalid = any(not dtr[1] for dtr in data_type_results)

        # flattened tuple of data types:
        data_types_from_services: DataTypesTuple = tuple(itertools.chain(*(dtr[0] for dtr in data_type_results)))

        new_now = datetime.now()

        await logger.adebug(
            "collected data types from data services",
            time_taken=(new_now - now).total_seconds(),
            n_data_types=len(data_types_from_services),
        )

        if not at_least_one_invalid:
            self._data_types[cache_key] = (new_now, data_types_from_services)

        return data_types_from_services


@cache
def get_data_type_manager(logger: LoggerDependency) -> DataTypeManager:
    """
    Gets a *singleton* instance of DataTypeManager
    """
    return DataTypeManager(logger)


DataTypeManagerDependency = Annotated[DataTypeManager, Depends(get_data_type_manager)]


async def get_data_types(
    # dependencies:
    authz_header: OptionalAuthzHeaderDependency,
    data_type_manager: DataTypeManagerDependency,
    http_session: HTTPSessionDependency,
    services_tuple: ServicesDependency,
    # scoping parameters - optionally can return counts/last ingestion only for a specific project/project+dataset:
    project: str | None = None,
    dataset: str | None = None,
) -> DataTypesTuple:
    return await data_type_manager.get_data_types(authz_header, http_session, services_tuple, project, dataset)


DataTypesDependency = Annotated[DataTypesTuple, Depends(get_data_types)]
