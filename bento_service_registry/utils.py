from .bento_services_json import BentoServicesByKind

__all__ = [
    "get_service_url",
]


def get_service_url(services_by_kind: BentoServicesByKind, service_kind: str) -> str:
    return services_by_kind[service_kind]["url"]
