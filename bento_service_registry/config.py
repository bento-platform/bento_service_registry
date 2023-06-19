from fastapi import Depends
from functools import lru_cache
from pathlib import Path
from pydantic import BaseConfig, BaseSettings
from typing import Annotated, Any, Literal

from .constants import SERVICE_TYPE

__all__ = [
    "Config",
    "get_config",
    "ConfigDependency",
]


DEFAULT_SERVICE_ID = ":".join(list(SERVICE_TYPE.values())[:2])


class Config(BaseSettings):
    bento_debug: bool = False
    bento_validate_ssl: bool = True

    bento_services: Path
    contact_timeout: int = 5

    bento_url: str
    bento_public_url: str
    bento_portal_public_url: str

    service_id: str = DEFAULT_SERVICE_ID

    bento_authz_service_url: str  # Bento authorization service base URL
    authz_enabled: bool = True

    cors_origins: tuple[str, ...] = ()

    log_level: Literal["debug", "info", "warning", "error"] = "debug"

    class Config(BaseConfig):
        # Make parent Config instances hashable + immutable
        allow_mutation = False
        frozen = True

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            if field_name == "cors_origins":
                return tuple(x.strip() for x in raw_val.split(";"))
            # noinspection PyUnresolvedReferences
            return cls.json_loads(raw_val)


@lru_cache
def get_config():
    return Config()


ConfigDependency = Annotated[Config, Depends(get_config)]
