import json

from fastapi import Depends
from functools import lru_cache
from pathlib import Path
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict
from typing import Annotated, Any, Literal

from .constants import SERVICE_TYPE

__all__ = [
    "Config",
    "get_config",
    "ConfigDependency",
]


class CorsOriginsParsingSource(EnvSettingsSource):
    def prepare_field_value(self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool) -> Any:
        if field_name == "cors_origins":
            return tuple(x.strip() for x in value.split(";")) if value is not None else ()
        return json.loads(value) if value_is_complex else value


DEFAULT_SERVICE_ID = ":".join(list(SERVICE_TYPE.values())[:2])


class Config(BaseSettings):
    bento_debug: bool = False
    bento_container_local: bool = False
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

    # Make Config instances hashable + immutable
    model_config = SettingsConfigDict(frozen=True)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (CorsOriginsParsingSource(settings_cls),)


@lru_cache
def get_config():
    return Config()


ConfigDependency = Annotated[Config, Depends(get_config)]
