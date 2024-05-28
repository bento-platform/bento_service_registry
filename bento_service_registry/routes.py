from fastapi import APIRouter, HTTPException, status

from .authz import authz_middleware
from .authz_header import OptionalAuthzHeaderDependency
from .bento_services_json import BentoServicesByKindDependency, BentoServicesByComposeIDDependency
from .data_types import DataTypesDependency, DataTypesTuple
from .http_session import HTTPSessionDependency
from .models import DataTypeWithServiceURL
from .service_info import ServiceInfoDependency
from .services import ServiceManagerDependency, ServicesDependency
from .workflows import WorkflowsByPurpose, WorkflowsDependency

__all__ = [
    "service_registry",
]

service_registry = APIRouter()


@service_registry.get("/bento-services", dependencies=[authz_middleware.dep_public_endpoint()])
async def bento_services(bento_services_by_compose_id: BentoServicesByComposeIDDependency):
    return bento_services_by_compose_id


@service_registry.get("/services", dependencies=[authz_middleware.dep_public_endpoint()])
async def list_services(services: ServicesDependency):
    return services


@service_registry.get("/services/types", dependencies=[authz_middleware.dep_public_endpoint()])
async def list_service_types(services_tuple: ServicesDependency) -> list[dict]:
    types_by_key: dict[str, dict] = {}
    for st in (s["type"] for s in services_tuple):
        sk = ":".join(st.values())
        types_by_key[sk] = st

    return list(types_by_key.values())


@service_registry.get("/services/{service_id}", dependencies=[authz_middleware.dep_public_endpoint()])
async def get_service_by_id(
    authz_header: OptionalAuthzHeaderDependency,
    bento_services_by_kind: BentoServicesByKindDependency,
    http_session: HTTPSessionDependency,
    service_info: ServiceInfoDependency,
    service_manager: ServiceManagerDependency,
    services_tuple: ServicesDependency,
    service_id: str,
):
    services_by_service_id = {s["id"]: s for s in services_tuple}

    if service_id not in services_by_service_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Service with ID {service_id} was not found in registry")

    svc = services_by_service_id[service_id]

    # Get service by bento.serviceKind, using type.artifact as a backup for legacy reasons
    service_data = await service_manager.get_service(
        authz_header,
        http_session,
        service_info,
        bento_services_by_kind[svc.get("bento", {}).get("serviceKind", svc["type"]["artifact"])],
    )

    if service_data is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"An internal error was encountered with service with ID {service_id}",
        )

    return service_data


@service_registry.get("/data-types", dependencies=[authz_middleware.dep_public_endpoint()])
async def list_data_types(data_types: DataTypesDependency) -> DataTypesTuple:
    return data_types


@service_registry.get("/data-types/{data_type_id}", dependencies=[authz_middleware.dep_public_endpoint()])
async def get_data_type(data_types: DataTypesDependency, data_type_id: str) -> DataTypeWithServiceURL:
    if (dt_res := {dt.id: dt for dt in data_types}.get(data_type_id)) is not None:
        return dt_res
    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Data type with ID {data_type_id} was not found")


@service_registry.get("/workflows", dependencies=[authz_middleware.dep_public_endpoint()])
async def list_workflows_by_purpose(workflows: WorkflowsDependency) -> WorkflowsByPurpose:
    return workflows


@service_registry.get("/service-info", dependencies=[authz_middleware.dep_public_endpoint()])
async def get_service_info(service_info: ServiceInfoDependency):
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info
    return service_info
