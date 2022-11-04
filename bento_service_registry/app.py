from __future__ import annotations

import os
import subprocess
import sys

from bento_lib.responses.quart_errors import (
    quart_error_wrap,
    quart_error_wrap_with_traceback,
    quart_internal_server_error,
    quart_bad_request_error,
    quart_not_found_error,
)
from quart import Quart
from werkzeug.exceptions import BadRequest, NotFound


from .constants import SERVICE_TYPE, SERVICE_NAME
from .routes import service_registry


def create_app():
    app = Quart(__name__)
    app.config.from_mapping(
        BENTO_DEBUG=os.environ.get("CHORD_DEBUG", os.environ.get("QUART_ENV", "production")).strip().lower() in (
            "true", "1", "development"),
        CHORD_SERVICES=os.environ.get("CHORD_SERVICES", os.environ.get("BENTO_SERVICES", "chord_services.json")),
        CHORD_URL=os.environ.get("CHORD_URL", os.environ.get("BENTO_URL", "http://0.0.0.0:5000/")),  # Own node's URL
        CONTACT_TIMEOUT=int(os.environ.get("CONTACT_TIMEOUT", 1)),
        SERVICE_ID=os.environ.get("SERVICE_ID", ":".join(SERVICE_TYPE.values())),
        URL_PATH_FORMAT=os.environ.get("URL_PATH_FORMAT", "api/{artifact}"),
    )

    path_for_git = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Generic catch-all
    app.register_error_handler(Exception, quart_error_wrap_with_traceback(
        quart_internal_server_error, sr_compat=True, service_name=SERVICE_NAME))
    app.register_error_handler(BadRequest, quart_error_wrap(quart_bad_request_error, sr_compat=True))
    app.register_error_handler(NotFound, quart_error_wrap(quart_not_found_error, sr_compat=True))

    app.register_blueprint(service_registry)

    @app.before_first_request
    async def before_first_request_func() -> None:
        try:
            # TODO: asyncify
            subprocess.run(["git", "config", "--global", "--add", "safe.directory", str(path_for_git)])
        except Exception as e:
            except_name = type(e).__name__
            print("Error in dev-mode retrieving git folder configuration", except_name, file=sys.stderr)

    return app


application = create_app()
