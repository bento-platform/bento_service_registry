from bento_lib.config.pydantic import BentoBaseConfig
from fastapi import Depends
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from .constants import SERVICE_TYPE

__all__ = [
    "Config",
    "get_config",
    "ConfigDependency",
]


DEFAULT_SERVICE_ID = ":".join(list(SERVICE_TYPE.values())[:2])


class Config(BentoBaseConfig):
    service_name: str = "Bento Service Registry"

    bento_services: Path
    contact_timeout: int = 5

    bento_url: str
    bento_public_url: str
    bento_portal_public_url: str

    authz_enabled: bool = True


@lru_cache
def get_config():
    return Config()


ConfigDependency = Annotated[Config, Depends(get_config)]
