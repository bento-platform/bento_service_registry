from async_lru import alru_cache
from bento_lib.service_info.helpers import build_service_info_from_pydantic_config
from bento_lib.service_info.types import GA4GHServiceInfo
from bento_service_registry import __version__
from fastapi import Depends
from logging import Logger
from typing import Annotated

from .config import Config, ConfigDependency
from .constants import BENTO_SERVICE_KIND, SERVICE_TYPE
from .logger import LoggerDependency


__all__ = [
    "get_service_info",
    "ServiceInfoDependency",
]


@alru_cache()
async def _get_service_info(config: Config, logger: Logger) -> GA4GHServiceInfo:
    return await build_service_info_from_pydantic_config(
        config,
        logger,
        {"serviceKind": BENTO_SERVICE_KIND},
        SERVICE_TYPE,
        __version__,
    )


async def get_service_info(config: ConfigDependency, logger: LoggerDependency) -> GA4GHServiceInfo:
    return await _get_service_info(config, logger)


ServiceInfoDependency = Annotated[GA4GHServiceInfo, Depends(get_service_info)]
