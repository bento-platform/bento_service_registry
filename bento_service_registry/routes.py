from fastapi import APIRouter, HTTPException, Request, status

from .authz import authz_middleware
from .bento_services_json import BentoServicesByKindDependency, BentoServicesByComposeIDDependency
from .config import ConfigDependency
from .http_session import HTTPSessionDependency
from .logger import LoggerDependency
from .service_info import get_service_info
from .services import get_service, get_services

__all__ = [
    "service_registry",
]

service_registry = APIRouter()


@service_registry.get("/bento-services", dependencies=[authz_middleware.dep_public_endpoint()])
async def bento_services(bento_services_by_compose_id: BentoServicesByComposeIDDependency):
    return bento_services_by_compose_id


@service_registry.get("/services", dependencies=[authz_middleware.dep_public_endpoint()])
async def services(
    bento_services_by_kind: BentoServicesByKindDependency,
    config: ConfigDependency,
    http_session: HTTPSessionDependency,
    logger: LoggerDependency,
    request: Request,
):
    return await get_services(bento_services_by_kind, config, http_session, logger, request)


@service_registry.get("/services/types", dependencies=[authz_middleware.dep_public_endpoint()])
async def service_types(
    bento_services_by_kind: BentoServicesByKindDependency,
    config: ConfigDependency,
    http_session: HTTPSessionDependency,
    logger: LoggerDependency,
    request: Request,
) -> list[dict]:
    types_by_key: dict[str, dict] = {}
    for st in (s["type"] for s in await get_services(
            bento_services_by_kind, config, http_session, logger, request)):
        sk = ":".join(st.values())
        types_by_key[sk] = st

    return list(types_by_key.values())


@service_registry.get("/services/{service_id}", dependencies=[authz_middleware.dep_public_endpoint()])
async def service_by_id(
    bento_services_by_kind: BentoServicesByKindDependency,
    config: ConfigDependency,
    http_session: HTTPSessionDependency,
    logger: LoggerDependency,
    request: Request,
    service_id: str,
):
    services_by_id = {
        s["id"]: s
        for s in (await get_services(bento_services_by_kind, config, http_session, logger, request))
    }

    if service_id not in services_by_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Service with ID {service_id} was not found in registry")

    svc = services_by_id[service_id]

    # Get service by bento.serviceKind, using type.artifact as a backup for legacy reasons
    service_data = await get_service(
        bento_services_by_kind,
        config,
        logger,
        request,
        http_session,
        bento_services_by_kind[svc.get("bento", {}).get("serviceKind", svc["type"]["artifact"])],
    )

    if service_data is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"An internal error was encountered with service with ID {service_id}")

    return service_data


@service_registry.get("/service-info", dependencies=[authz_middleware.dep_public_endpoint()])
async def service_info(
    bento_services_by_kind: BentoServicesByKindDependency,
    config: ConfigDependency,
    logger: LoggerDependency,
):
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info
    return await get_service_info(bento_services_by_kind, config, logger)
