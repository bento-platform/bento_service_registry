from bento_lib.responses.fastapi_errors import http_exception_handler_factory, validation_exception_handler_factory
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .authz import authz_middleware
from .config import get_config
from .logger import get_logger
from .routes import service_registry

__all__ = [
    "application",
]


application = FastAPI()
application.include_router(service_registry)

# TODO: Find a way to DI this
config_for_setup = get_config()

application.add_middleware(
    CORSMiddleware,
    allow_origins=config_for_setup.cors_origins,
    allow_headers=["Authorization"],
    allow_credentials=True,
    allow_methods=["*"],
)

# Non-standard middleware setup so that we can import the instance and use it for dependencies too
authz_middleware.attach(application)

application.exception_handler(StarletteHTTPException)(
    http_exception_handler_factory(get_logger(config_for_setup), authz_middleware))
application.exception_handler(RequestValidationError)(validation_exception_handler_factory(authz_middleware))
