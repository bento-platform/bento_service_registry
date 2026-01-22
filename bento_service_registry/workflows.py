import aiohttp
import asyncio
import structlog.stdlib

from datetime import datetime
from fastapi import Depends, status
from functools import cache
from typing import Annotated
from urllib.parse import urljoin

from .authz_header import OptionalHeaders, OptionalAuthzHeaderDependency
from .config import Config, ConfigDependency
from .http_session import HTTPSessionDependency
from .logger import LoggerDependency
from .services import ServicesDependency
from .utils import right_slash_normalize_url, authz_header_digest

__all__ = [
    "WorkflowsByPurpose",
    "get_workflows",
    "WorkflowsDependency",
]


WorkflowsByPurpose = dict[str, dict[str, dict]]


class WorkflowManager:
    def __init__(self, config: Config, logger: structlog.stdlib.BoundLogger):
        self._config: Config = config
        self._logger = logger

        # cache
        self._n_workflow_providers: int | None = None
        self._workflows_by_purpose: dict[str, tuple[datetime, WorkflowsByPurpose]] = {}

    def _clean_cache(self):
        now = datetime.now()
        for k, v in self._workflows_by_purpose.items():
            if (now - v[0]).total_seconds() >= self._config.workflow_cache_ttl:
                del self._workflows_by_purpose[k]

    async def get_workflows_from_service(
        self,
        authz_header: OptionalHeaders,
        http_session: aiohttp.ClientSession,
        service: dict,
        start_dt: datetime,
    ) -> WorkflowsByPurpose:
        service_url: str | None = service.get("url")

        if service_url is None:
            await self._logger.aerror("encountered service missing URL", service=service)
            return {}

        service_url_norm: str = right_slash_normalize_url(service_url)
        workflows_url: str = urljoin(service_url_norm, "workflows")

        logger = self._logger.bind(workflows_url=workflows_url)

        try:
            async with http_session.get(workflows_url, headers=authz_header) as res:
                data = await res.json()
                time_taken = (datetime.now() - start_dt).total_seconds()

                logger = logger.bind(time_taken=time_taken)

                if res.status != status.HTTP_200_OK:
                    await logger.aerror(
                        "got non-200 response from workflow-providing service",
                        status=res.status,
                        body=data,
                    )
                    return {}
        except asyncio.TimeoutError:
            await logger.aerror("service workflow fetch timeout error")
            return {}
        except aiohttp.ClientConnectionError as e:
            await logger.aexception("service workflow fetch connection error", exc_info=e)
            return {}

        await logger.adebug("fetching service workflows complete")

        wfs: dict[str, dict[str, dict]] = {}

        for purpose, purpose_wfs in data.items():
            if purpose not in wfs:
                wfs[purpose] = {}
            # TODO: pydantic model + validation
            wfs[purpose].update({k: {**wf, "service_base_url": service_url_norm} for k, wf in purpose_wfs.items()})

        return wfs

    async def get_workflows(
        self,
        authz_header: OptionalHeaders,
        http_session: aiohttp.ClientSession,
        services_tuple: tuple[dict, ...],
    ):
        now = datetime.now()

        await self._logger.adebug("collecting workflows from workflow-providing services")

        workflow_services = [
            s
            for s in services_tuple
            if (b := s.get("bento", {})).get("dataService", False) or b.get("workflowProvider", False)
        ]
        n_workflow_providers = len(workflow_services)
        logger = self._logger.bind(n_workflow_providers=n_workflow_providers)

        cache_key = authz_header_digest(authz_header)

        if (
            n_workflow_providers == self._n_workflow_providers
            and (wfp := self._workflows_by_purpose.get(cache_key)) is not None
            and (now - wfp[0]).total_seconds() < self._config.workflow_cache_ttl
        ):
            # If:
            #  - the number of workflow-providing services hasn't changed
            #  - our cache is populated
            #  - our cache has not expired
            # then use it!
            await logger.adebug(
                "returning workflows from cache",
                time_taken=(datetime.now() - now).total_seconds(),
                n_workflows_found=len(wfp[1]),
            )
            return wfp[1]

        # Otherwise, (re-)populate the cache.

        self._n_workflow_providers = n_workflow_providers

        await logger.adebug("done collecting workflow-providing services")

        if not workflow_services:
            self._workflows_by_purpose = (now, {})
            return {}

        service_wfs = await asyncio.gather(
            *(self.get_workflows_from_service(authz_header, http_session, s, now) for s in workflow_services)
        )

        workflows_from_services: WorkflowsByPurpose = {}
        n_workflows_found: int = 0

        for s_wfs in service_wfs:
            for purpose, purpose_wfs in s_wfs.items():
                if purpose not in workflows_from_services:
                    workflows_from_services[purpose] = {}
                workflows_from_services[purpose].update(purpose_wfs)
                n_workflows_found += len(purpose_wfs)

        new_now = datetime.now()

        await logger.adebug(
            "done collecting workflows",
            time_taken=(new_now - now).total_seconds(),
            n_workflows_found=n_workflows_found,
        )

        self._workflows_by_purpose[cache_key] = (new_now, workflows_from_services)

        # Clean up old cache entries
        self._clean_cache()

        return workflows_from_services


@cache
def get_workflow_manager(config: ConfigDependency, logger: LoggerDependency) -> WorkflowManager:
    """
    Gets a *singleton* instance of WorkflowManager
    """
    return WorkflowManager(config, logger)


WorkflowManagerDependency = Annotated[WorkflowManager, Depends(get_workflow_manager)]


async def get_workflows(
    authz_header: OptionalAuthzHeaderDependency,
    http_session: HTTPSessionDependency,
    services_tuple: ServicesDependency,
    workflow_manager: WorkflowManagerDependency,
) -> WorkflowsByPurpose:
    return await workflow_manager.get_workflows(authz_header, http_session, services_tuple)


WorkflowsDependency = Annotated[WorkflowsByPurpose, Depends(get_workflows)]
