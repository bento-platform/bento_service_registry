import aiohttp
import asyncio
import logging

from fastapi import Depends, status
from typing import Annotated
from urllib.parse import urljoin

from .authz_header import OptionalAuthzHeader, OptionalAuthzHeaderDependency
from .http_session import HTTPSessionDependency
from .logger import LoggerDependency
from .services import ServicesDependency

__all__ = [
    "WorkflowsByPurpose",
    "get_workflows",
    "WorkflowsDependency",
]


WorkflowsByPurpose = dict[str, dict[str, dict]]


async def get_workflows_from_service(
    authz_header: OptionalAuthzHeader,
    http_session: aiohttp.ClientSession,
    logger: logging.Logger,
    service: dict,
) -> WorkflowsByPurpose:
    service_url: str | None = service.get("url")

    if service_url is None:
        logger.error(f"Encountered a service missing a URL: {service}")
        return {}

    service_url_norm: str = service_url.rstrip("/") + "/"

    async with http_session.get(urljoin(service_url_norm, "workflows"), headers=authz_header) as res:
        if res.status != status.HTTP_200_OK:
            logger.error(
                f"Got non-200 response from data type service ({service_url=}): {res.status=}; body={await res.json()}")
            return {}

        wfs: dict[str, dict[str, dict]] = {}

        for purpose, purpose_wfs in (await res.json()).items():
            if purpose not in wfs:
                wfs[purpose] = {}
            # TODO: pydantic model + validation
            wfs[purpose].update({k: {**wf, "service_base_url": service_url_norm} for k, wf in purpose_wfs.items()})

        return wfs


async def get_workflows(
    authz_header: OptionalAuthzHeaderDependency,
    http_session: HTTPSessionDependency,
    logger: LoggerDependency,
    services_tuple: ServicesDependency,
) -> WorkflowsByPurpose:
    logger.debug("Collecting workflows from workflow-providing services")

    workflow_services = [
        s for s in services_tuple
        if (b := s.get("bento", {})).get("dataService", False) or b.get("workflowProvider", False)
    ]

    logger.debug(f"Found {len(workflow_services)} workflow-providing services")

    service_wfs = await asyncio.gather(
        *(get_workflows_from_service(authz_header, http_session, logger, s) for s in workflow_services)
    )

    workflows_from_services: WorkflowsByPurpose = {}
    workflows_found: int = 0

    for s_wfs in service_wfs:
        for purpose, purpose_wfs in s_wfs.items():
            if purpose not in workflows_from_services:
                workflows_from_services[purpose] = {}
            workflows_from_services[purpose].update(purpose_wfs)
            workflows_found += len(purpose_wfs)

    logger.debug(f"Obtained {workflows_found} workflows")

    return workflows_from_services


WorkflowsDependency = Annotated[WorkflowsByPurpose, Depends(get_workflows)]
