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

TRUTH_VALUES = ("true", "1")


def get_bento_debug():
    # This is a function to allow monkey-patching the environment on app startup.
    return os.environ.get(
        "CHORD_DEBUG", os.environ.get("BENTO_DEBUG", os.environ.get("QUART_ENV", "production"))
    ).strip().lower() in (*TRUTH_VALUES, "development")


def create_app():
    app = Quart(__name__)
    bento_url = os.environ.get("CHORD_URL", os.environ.get("BENTO_URL", "http://0.0.0.0:5000/"))  # Own node's URL

    bento_debug = get_bento_debug()
    validate_ssl = os.environ.get("BENTO_VALIDATE_SSL", str(not bento_debug)).strip().lower() in TRUTH_VALUES

    app.config.from_mapping(
        BENTO_DEBUG=bento_debug,
        BENTO_VALIDATE_SSL=validate_ssl,
        BENTO_SERVICES=os.environ.get("CHORD_SERVICES", os.environ.get("BENTO_SERVICES", "chord_services.json")),
        BENTO_URL=bento_url,
        BENTO_PUBLIC_URL=os.environ.get("BENTO_PUBLIC_URL", bento_url),
        BENTO_PORTAL_PUBLIC_URL=os.environ.get("BENTO_PORTAL_PUBLIC_URL", bento_url),
        CONTACT_TIMEOUT=int(os.environ.get("CONTACT_TIMEOUT", 5)),
        SERVICE_ID=os.environ.get("SERVICE_ID", ":".join(SERVICE_TYPE.values())),
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
