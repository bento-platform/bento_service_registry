from bento_lib.service_info import SERVICE_ORGANIZATION_C3G, GA4GHServiceInfo, build_service_info
from bento_service_registry import __version__
from fastapi import Depends
from typing import Annotated

from .bento_services_json import BentoServicesByKindDependency
from .config import ConfigDependency
from .constants import BENTO_SERVICE_KIND, SERVICE_NAME, SERVICE_TYPE
from .logger import LoggerDependency
from .utils import get_service_url


__all__ = [
    "get_service_info",
    "ServiceInfoDependency",
]


async def get_service_info(
    bento_services_by_kind: BentoServicesByKindDependency,
    config: ConfigDependency,
    logger: LoggerDependency,
) -> GA4GHServiceInfo:
    return await build_service_info({
        "id": config.service_id,
        "name": SERVICE_NAME,  # TODO: Should be globally unique?
        "type": SERVICE_TYPE,
        "description": "Service registry for a Bento platform node.",
        "organization": SERVICE_ORGANIZATION_C3G,
        "contactUrl": "mailto:info@c3g.ca",
        "version": __version__,
        "url": get_service_url(bento_services_by_kind, BENTO_SERVICE_KIND),
        "environment": "prod",
        "bento": {
            "serviceKind": BENTO_SERVICE_KIND,
        },
    }, debug=config.bento_debug, local=config.bento_container_local, logger=logger)


ServiceInfoDependency = Annotated[GA4GHServiceInfo, Depends(get_service_info)]
