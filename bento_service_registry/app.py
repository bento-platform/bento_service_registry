from bento_lib.responses.fastapi_errors import http_exception_handler_factory, validation_exception_handler_factory
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Callable

from .authz import authz_middleware
from .config import Config, get_config
from .logger import get_logger
from .routes import service_registry

__all__ = [
    "create_app",
]


def create_app(config_override: Callable[[], Config] | None = None) -> FastAPI:
    app = FastAPI()

    config_for_setup: Config = (config_override or get_config)()
    if config_override:
        # noinspection PyUnresolvedReferences
        app.dependency_overrides[get_config] = config_override

    app.include_router(service_registry)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config_for_setup.cors_origins,
        allow_headers=["Authorization"],
        allow_credentials=True,
        allow_methods=["*"],
    )

    # Non-standard middleware setup so that we can import the instance and use it for dependencies too
    authz_middleware.attach(app)

    app.exception_handler(StarletteHTTPException)(
        http_exception_handler_factory(get_logger(config_for_setup), authz_middleware))
    app.exception_handler(RequestValidationError)(validation_exception_handler_factory(authz_middleware))

    return app
