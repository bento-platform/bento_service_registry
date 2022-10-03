import bento_service_registry
import os
import requests
import sys
import subprocess

from bento_lib.responses.flask_errors import (
    flask_error_wrap,
    flask_error_wrap_with_traceback,
    flask_internal_server_error,
    flask_bad_request_error,
    flask_not_found_error,
)
from flask import Flask, current_app, json, jsonify, request
from json.decoder import JSONDecodeError
from urllib.parse import urljoin
from werkzeug.exceptions import BadRequest, NotFound


SERVICE_ARTIFACT = "service-registry"
SERVICE_TYPE = f"ca.c3g.bento:{SERVICE_ARTIFACT}:{bento_service_registry.__version__}"
SERVICE_NAME = "Bento Service Registry"


application = Flask(__name__)

application.config.from_mapping(
    BENTO_DEBUG=os.environ.get("CHORD_DEBUG", os.environ.get("FLASK_ENV", "production")).strip().lower() in (
        "true", "1", "development"),
    CHORD_SERVICES=os.environ.get("CHORD_SERVICES", os.environ.get("BENTO_SERVICES", "chord_services.json")),
    CHORD_URL=os.environ.get("CHORD_URL", os.environ.get("BENTO_URL", "http://127.0.0.1:5000/")),  # Own node's URL
    CONTACT_TIMEOUT=int(os.environ.get("CONTACT_TIMEOUT", 1)),
    SERVICE_ID=os.environ.get("SERVICE_ID", SERVICE_TYPE),
    URL_PATH_FORMAT=os.environ.get("URL_PATH_FORMAT", "api/{artifact}"),
)

path_for_git = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Generic catch-all
application.register_error_handler(Exception, flask_error_wrap_with_traceback(flask_internal_server_error,
                                                                              sr_compat=True,
                                                                              service_name=SERVICE_NAME))
application.register_error_handler(BadRequest, flask_error_wrap(flask_bad_request_error, sr_compat=True))
application.register_error_handler(NotFound, flask_error_wrap(flask_not_found_error, sr_compat=True))


def get_service_url(artifact: str):
    return urljoin(current_app.config["CHORD_URL"], current_app.config["URL_PATH_FORMAT"].format(artifact=artifact))


def get_chord_services():
    """
    Reads the list of services from the chord_services.json file
    """
    services = []
    try:
        with open(current_app.config["CHORD_SERVICES"], "r") as f:
            services = [s for s in json.load(f) if not s.get("disabled")]  # Skip disabled services
    except Exception as e:
        except_name = type(e).__name__
        print("Error in retrieving services information from json file.", except_name)
    return services


with application.app_context():
    SERVICE_ID = current_app.config["SERVICE_ID"]
    SERVICE_INFO = {
        "id": SERVICE_ID,
        "name": SERVICE_NAME,  # TODO: Should be globally unique?
        "type": SERVICE_TYPE,
        "description": "Service registry for a Bento platform node.",
        "organization": {
            "name": "C3G",
            "url": "http://www.computationalgenomics.ca"
        },
        "contactUrl": "mailto:david.lougheed@mail.mcgill.ca",
        "version": bento_service_registry.__version__,
        "url": get_service_url(SERVICE_ARTIFACT),
        "environment": "prod"
    }

    chord_services_content = get_chord_services()   # Not a constant: can change when a service is updated



def get_service(service_artifact):
    # special case: requesting info about the current service. Avoids request timeout
    # when running gunicorn on a single worker
    if service_artifact == SERVICE_ARTIFACT:
        return _service_info()

    s_url = get_service_url(service_artifact)
    service_info_url = urljoin(f"{s_url}/", "service-info")

    print(f"[{SERVICE_NAME}] Contacting {service_info_url}", flush=True)

    # Optional Authorization HTTP header to forward to nested requests
    # TODO: Move X-Auth... constant to bento_lib
    auth_header = request.headers.get("X-Authorization", request.headers.get("Authorization"))

    service_resp = {}

    try:
        r = requests.get(
            service_info_url,
            headers={"Authorization": auth_header} if auth_header else {},
            timeout=current_app.config["CONTACT_TIMEOUT"],
            verify=not current_app.config["BENTO_DEBUG"],
        )

        if r.status_code != 200:
            print(f"[{SERVICE_NAME}] Non-200 status code on {service_artifact}: {r.status_code}\n"
                    f"                 Content: {r.text}", file=sys.stderr, flush=True)

            # If we have the special case where we got a JWT error from the proxy script, we can safely print out
            # headers for debugging, since the JWT leaked isn't valid anyway.
            if "invalid jwt" in r.text:
                print(f"                 Encountered auth error, tried to use header: {auth_header}",
                        file=sys.stderr, flush=True)

            return None

    except requests.exceptions.Timeout:
        print(f"[{SERVICE_NAME}] Encountered timeout with {service_info_url}", file=sys.stderr, flush=True)
        return None

    try:
        service_resp[service_artifact] = {**r.json(), "url": s_url}
    except JSONDecodeError:
        print(f"[{SERVICE_NAME}] Encountered invalid response from {service_info_url}: {r.text}")
        return None

    return service_resp[service_artifact]


@application.before_first_request
def before_first_request_func():
    try:
        subprocess.run(["git", "config", "--global", "--add", "safe.directory", str(path_for_git)])
    except Exception as e:
        except_name = type(e).__name__
        print("Error in dev-mode retrieving git folder configuration", except_name)


@application.route("/bento-services")
@application.route("/chord-services")
def chord_services():
    return jsonify(get_chord_services())


def _services():
    return [s for s in (
        get_service(s["type"]["artifact"]) for s in chord_services_content
        ) if s is not None]


@application.route("/services")
def services():
    return jsonify(_services())


@application.route("/services/<string:service_id>")
def service_by_id(service_id):
    services_by_id = {s["id"]: s for s in _services()}
    if service_id not in services_by_id:
        return flask_not_found_error(f"Service with ID {service_id} was not found in registry")

    service_artifact = services_by_id[service_id]["type"].split(":")[1]
    return get_service(service_artifact)


@application.route("/services/types")
def service_types():
    return jsonify(sorted(set(s["type"] for s in _services())))


def _service_info():
    if not current_app.config["BENTO_DEBUG"]:
        return SERVICE_INFO

    info = {
        **SERVICE_INFO,
        "environment": "dev"
    }
    try:
        res_tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"])
        if res_tag:
            info["git_tag"] = res_tag.decode().rstrip()
        res_branch = subprocess.check_output(["git", "branch", "--show-current"])
        if res_branch:
            info["git_branch"] = res_branch.decode().rstrip()

    except Exception as e:
        except_name = type(e).__name__
        print("Error in dev-mode retrieving git information", except_name)

    return info  # updated service info with the git info

@application.route("/service-info")
def service_info():
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info
    return jsonify(_service_info())
