import aiohttp
import asyncio
import itertools
import structlog.stdlib

from fastapi import Depends, status
from pydantic import ValidationError
from typing import Annotated
from urllib.parse import urlencode, urljoin

from .authz_header import OptionalHeaders, OptionalAuthzHeaderDependency
from .http_session import HTTPSessionDependency
from .logger import LoggerDependency
from .models import DataTypeWithServiceURL
from .services import ServicesDependency

__all__ = [
    "DataTypesTuple",
    "get_data_types",
    "DataTypesDependency",
]


DataTypesTuple = tuple[DataTypeWithServiceURL, ...]


async def get_data_types_from_service(
    authz_header: OptionalHeaders,
    http_session: aiohttp.ClientSession,
    logger: structlog.stdlib.BoundLogger,
    service: dict,
    project: str | None,
    dataset: str | None,
) -> DataTypesTuple:
    service_url: str | None = service.get("url")

    if service_url is None:
        await logger.aerror(f"Encountered a service missing a URL: {service}")
        return ()

    service_url_norm: str = service_url.rstrip("/") + "/"

    qp = {}
    if project:
        qp["project"] = project
    if dataset:
        qp["dataset"] = dataset

    async with http_session.get(
        urljoin(service_url_norm, "data-types") + (f"?{urlencode(qp)}" if qp else ""), headers=authz_header
    ) as res:
        if res.status != status.HTTP_200_OK:
            await logger.aerror(
                f"Got non-200 response from data type service ({service_url=}): {res.status=}; body={await res.json()}"
            )
            return ()

        dts: list[DataTypeWithServiceURL] = []

        for dt in await res.json():
            try:
                dts.append(DataTypeWithServiceURL.model_validate({**dt, "service_base_url": service_url_norm}))
            except ValidationError as err:
                await logger.aerror(f"Recieved malformatted data type: {dt} ({err=}); skipping")
                continue

        return tuple(dts)


async def get_data_types(
    # dependencies:
    authz_header: OptionalAuthzHeaderDependency,
    http_session: HTTPSessionDependency,
    logger: LoggerDependency,
    services_tuple: ServicesDependency,
    # scoping parameters - optionally can return counts/last ingestion only for a specific project/project+dataset:
    project: str | None = None,
    dataset: str | None = None,
) -> DataTypesTuple:
    data_services = [s for s in services_tuple if s.get("bento", {}).get("dataService", False)]

    data_types_from_services: tuple[DataTypeWithServiceURL, ...] = tuple(
        itertools.chain(
            *await asyncio.gather(
                *(
                    get_data_types_from_service(authz_header, http_session, logger, s, project, dataset)
                    for s in data_services
                )
            )
        )
    )

    await logger.adebug(
        "collected data types from data services",
        project=project,
        dataset=dataset,
        n_data_services=len(data_services),
        n_data_types=len(data_types_from_services),
    )

    return data_types_from_services


DataTypesDependency = Annotated[DataTypesTuple, Depends(get_data_types)]
