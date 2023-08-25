from fastapi import APIRouter, HTTPException, Request, status

from .authz import authz_middleware
from .bento_services_json import BentoServicesByKindDependency, BentoServicesByComposeIDDependency
from .http_session import HTTPSessionDependency
from .logger import LoggerDependency
from .service_info import ServiceInfoDependency
from .services import get_service, ServicesDependency

__all__ = [
    "service_registry",
]

service_registry = APIRouter()


@service_registry.get("/bento-services", dependencies=[authz_middleware.dep_public_endpoint()])
async def bento_services(bento_services_by_compose_id: BentoServicesByComposeIDDependency):
    return bento_services_by_compose_id


@service_registry.get("/services", dependencies=[authz_middleware.dep_public_endpoint()])
async def services(services_tuple: ServicesDependency):
    return services_tuple


@service_registry.get("/services/types", dependencies=[authz_middleware.dep_public_endpoint()])
async def service_types(services_tuple: ServicesDependency) -> list[dict]:
    types_by_key: dict[str, dict] = {}
    for st in (s["type"] for s in services_tuple):
        sk = ":".join(st.values())
        types_by_key[sk] = st

    return list(types_by_key.values())


@service_registry.get("/services/{service_id}", dependencies=[authz_middleware.dep_public_endpoint()])
async def service_by_id(
    bento_services_by_kind: BentoServicesByKindDependency,
    http_session: HTTPSessionDependency,
    logger: LoggerDependency,
    request: Request,
    service_info_contents: ServiceInfoDependency,
    services_tuple: ServicesDependency,
    service_id: str,
):
    services_by_service_id = {s["id"]: s for s in services_tuple}

    if service_id not in services_by_service_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Service with ID {service_id} was not found in registry")

    svc = services_by_service_id[service_id]

    # Get service by bento.serviceKind, using type.artifact as a backup for legacy reasons
    service_data = await get_service(
        logger,
        request,
        http_session,
        service_info_contents,
        bento_services_by_kind[svc.get("bento", {}).get("serviceKind", svc["type"]["artifact"])],
    )

    if service_data is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"An internal error was encountered with service with ID {service_id}")

    return service_data


@service_registry.get("/service-info", dependencies=[authz_middleware.dep_public_endpoint()])
async def service_info(service_info_contents: ServiceInfoDependency):
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info
    return service_info_contents
