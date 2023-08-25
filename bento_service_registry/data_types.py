import aiohttp
import asyncio
import itertools
import logging

from fastapi import Depends, status
from typing import Annotated
from urllib.parse import urljoin

from .http_session import HTTPSessionDependency
from .logger import LoggerDependency
from .models import DataTypeDefinitionWithServiceURL
from .services import ServicesDependency

__all__ = [
    "DataTypesTuple",
    "get_data_types",
    "DataTypesDependency",
]


DataTypesTuple = tuple[DataTypeDefinitionWithServiceURL, ...]


async def get_data_types_from_service(
    http_session: aiohttp.ClientSession,
    logger: logging.Logger,
    service: dict,
) -> DataTypesTuple:
    service_url: str | None = service.get("url")

    if service_url is None:
        logger.error(f"Encountered a service missing a URL: {service}")
        return ()

    service_url_with_trailing_slash: str = service_url.rstrip("/") + "/"

    async with http_session.get(urljoin(service_url_with_trailing_slash, "data-types")) as res:
        if res.status != status.HTTP_200_OK:
            logger.error(
                f"Got non-200 response from data type service ({service_url=}): {res.status=}; body={await res.json()}")
            return ()

        return tuple(
            DataTypeDefinitionWithServiceURL.model_validate({**dt, "service_base_url": service_url_with_trailing_slash})
            for dt in await res.json()
        )


async def get_data_types(
    http_session: HTTPSessionDependency,
    logger: LoggerDependency,
    services_tuple: ServicesDependency,
) -> DataTypesTuple:
    logger.debug("Collecting data types from data services")

    data_services = [s for s in services_tuple if s.get("bento", {}).get("dataService", False)]

    logger.debug(f"Found {len(data_services)} data services")

    data_types_from_services: tuple[DataTypeDefinitionWithServiceURL, ...] = tuple(
        itertools.chain(
            *await asyncio.gather(*(
                get_data_types_from_service(http_session, logger, s) for s in data_services
            ))
        )
    )

    logger.debug(f"Obtained {len(data_types_from_services)} data types")

    return data_types_from_services


DataTypesDependency = Annotated[DataTypesTuple, Depends(get_data_types)]
