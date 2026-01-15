import aiohttp
import asyncio
import itertools
import structlog.stdlib

from datetime import datetime
from fastapi import Depends, status
from pydantic import ValidationError
from typing import Annotated
from urllib.parse import urlencode, urljoin

from .authz_header import OptionalHeaders, OptionalAuthzHeaderDependency
from .http_session import HTTPSessionDependency
from .logger import LoggerDependency
from .models import DataTypeWithServiceURL
from .services import ServicesDependency
from .utils import right_slash_normalize_url

__all__ = [
    "DataTypesTuple",
    "get_data_types",
    "DataTypesDependency",
]


DataTypesTuple = tuple[DataTypeWithServiceURL, ...]


def build_scope_query_params(project: str | None, dataset: str | None) -> str:
    qp = {}
    if project:
        qp["project"] = project
    if dataset:
        qp["dataset"] = dataset
    return f"?{urlencode(qp)}" if qp else ""


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
        await logger.aerror("encountered service with missing URL", service=service)
        return ()

    service_url_norm: str = right_slash_normalize_url(service_url)
    data_types_url = urljoin(service_url_norm, "data-types") + build_scope_query_params(project, dataset)

    logger = logger.bind(data_types_url=data_types_url)

    try:
        async with http_session.get(data_types_url, headers=authz_header) as res:
            data = await res.json()
            if res.status != status.HTTP_200_OK:
                await logger.aerror("got non-200 response from data type service", status=res.status, body=data)
                return ()
    except asyncio.TimeoutError:
        await logger.aerror("service data type fetch timeout error")
        return ()
    except aiohttp.ClientConnectionError as e:
        await logger.aexception("service data type fetch connection error", exc_info=e)
        return ()

    dts: list[DataTypeWithServiceURL] = []

    for dt in data:
        try:
            dts.append(DataTypeWithServiceURL.model_validate({**dt, "service_base_url": service_url_norm}))
        except ValidationError as err:
            await logger.aerror("skipping recieved malformatted data type", data_type=dt, exc_info=err)
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

    logger = logger.bind(project=project, dataset=dataset)

    start_dt = datetime.now()

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
        time_taken=(datetime.now() - start_dt).total_seconds(),
        n_data_services=len(data_services),
        n_data_types=len(data_types_from_services),
    )

    return data_types_from_services


DataTypesDependency = Annotated[DataTypesTuple, Depends(get_data_types)]
