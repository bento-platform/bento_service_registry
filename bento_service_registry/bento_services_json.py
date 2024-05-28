import aiofiles
import orjson
from async_lru import alru_cache
from fastapi import Depends

from typing import Annotated

from .config import Config, ConfigDependency
from .types import BentoService


__all__ = [
    "BentoServicesByComposeID",
    "BentoServicesByKind",
    "get_bento_services_by_compose_id",
    "BentoServicesByComposeIDDependency",
    "get_bento_services_by_kind",
    "BentoServicesByKindDependency",
]


BentoServicesByComposeID = dict[str, BentoService]
BentoServicesByKind = dict[str, BentoService]


# cache bento_services.json contents for the lifetime of the service:
@alru_cache()
async def _get_bento_services_by_compose_id(config: Config) -> BentoServicesByComposeID:
    async with aiofiles.open(config.bento_services, "rb") as fh:
        bento_services_data: BentoServicesByComposeID = orjson.loads(await fh.read())

    return {
        sk: BentoService(
            **sv,
            url=sv["url_template"].format(
                BENTO_URL=config.bento_url,
                BENTO_PUBLIC_URL=config.bento_public_url,
                BENTO_PORTAL_PUBLIC_URL=config.bento_portal_public_url,
                **sv,
            ),
        )  # type: ignore
        for sk, sv in bento_services_data.items()
        # Filter out disabled entries and entries without service_kind, which may be external/'transparent'
        # - e.g., the gateway.
        if not sv.get("disabled") and sv.get("service_kind")
    }


async def get_bento_services_by_compose_id(config: ConfigDependency) -> BentoServicesByComposeID:
    return await _get_bento_services_by_compose_id(config)


BentoServicesByComposeIDDependency = Annotated[BentoServicesByComposeID, Depends(get_bento_services_by_compose_id)]


async def get_bento_services_by_kind(
    bento_services_by_compose_id: BentoServicesByComposeIDDependency,
) -> BentoServicesByKind:
    services_by_kind: BentoServicesByKind = {}

    for sv in bento_services_by_compose_id.values():
        # Disabled entries are already filtered out by get_bento_services_by_compose_id
        # Filter out entries without service_kind, which may be external/'transparent' - e.g., the gateway.
        if sk := sv.get("service_kind"):
            services_by_kind[sk] = sv

    return services_by_kind


BentoServicesByKindDependency = Annotated[BentoServicesByKind, Depends(get_bento_services_by_kind)]
