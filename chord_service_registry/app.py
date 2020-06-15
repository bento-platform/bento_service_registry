import chord_service_registry
import os
import requests
import sys

from chord_lib.responses.flask_errors import *
from flask import Flask, json, jsonify
from urllib.parse import urljoin
from werkzeug.exceptions import BadRequest, NotFound


TIMEOUT = 1


SERVICE_ARTIFACT = "service-registry"
SERVICE_TYPE = f"ca.c3g.chord:{SERVICE_ARTIFACT}:{chord_service_registry.__version__}"
SERVICE_ID = os.environ.get("SERVICE_ID", SERVICE_TYPE)
SERVICE_NAME = "CHORD Service Registry"

SERVICE_INFO = {
    "id": SERVICE_ID,
    "name": SERVICE_NAME,  # TODO: Should be globally unique?
    "type": SERVICE_TYPE,
    "description": "Service registry for a CHORD application.",
    "organization": {
        "name": "C3G",
        "url": "http://www.computationalgenomics.ca"
    },
    "contactUrl": "mailto:david.lougheed@mail.mcgill.ca",
    "version": chord_service_registry.__version__
}

URL_PATH_FORMAT = os.environ.get("URL_PATH_FORMAT", "api/{artifact}")

CHORD_URL = os.environ.get("CHORD_URL", "http://127.0.0.1:5000/")  # Own node's URL
CHORD_SERVICES_PATH = os.environ.get("CHORD_SERVICES", "chord_services.json")
with open(CHORD_SERVICES_PATH, "r") as f:
    CHORD_SERVICES = [s for s in json.load(f) if not s.get("disabled")]  # Skip disabled services


application = Flask(__name__)
application.config.from_mapping(CHORD_SERVICES=CHORD_SERVICES_PATH)

# Generic catch-all
application.register_error_handler(Exception, flask_error_wrap_with_traceback(flask_internal_server_error,
                                                                              service_name=SERVICE_NAME))
application.register_error_handler(BadRequest, flask_error_wrap(flask_bad_request_error))
application.register_error_handler(NotFound, flask_error_wrap(flask_not_found_error))


def get_service_url(artifact: str):
    return urljoin(CHORD_URL, URL_PATH_FORMAT.format(artifact=artifact))


service_info_cache = {
    # Pre-populate service-info cache with data for the current service
    SERVICE_ARTIFACT: {**SERVICE_INFO, "url": get_service_url(SERVICE_ARTIFACT)},
}


def get_service(s):
    s_artifact = s["type"]["artifact"]
    s_url = urljoin(CHORD_URL, URL_PATH_FORMAT.format(artifact=s_artifact))

    if s_artifact not in service_info_cache:
        service_info_url = urljoin(f"{s_url}/", "service-info")

        print(f"[{SERVICE_NAME}] Contacting {service_info_url}", flush=True)

        try:
            r = requests.get(service_info_url, timeout=TIMEOUT)
            if r.status_code != 200:
                print(f"[{SERVICE_NAME}] Non-200 status code on {s_artifact}: {r.status_code}", file=sys.stderr,
                      flush=True)
                return None
        except requests.exceptions.Timeout:
            print(f"[{SERVICE_NAME}] Encountered timeout with {service_info_url}", file=sys.stderr, flush=True)
            return None

        service_info_cache[s_artifact] = {**r.json(), "url": s_url}

    return service_info_cache[s_artifact]


@application.route("/chord-services")
def chord_services():
    return jsonify(CHORD_SERVICES)


@application.route("/services")
def services():
    return jsonify([s for s in (get_service(s) for s in CHORD_SERVICES) if s is not None])


@application.route("/services/<string:service_id>")
def service_by_id(service_id):
    services_by_id = {s["id"]: s for s in service_info_cache.values()}
    if service_id not in services_by_id:
        return flask_not_found_error(f"Service with ID {service_id} was not found in registry")

    return get_service(services_by_id[service_id])


@application.route("/services/types")
def service_types():
    return jsonify(sorted(set(s["type"] for s in service_info_cache.values())))


@application.route("/service-info")
def service_info():
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info
    return jsonify(SERVICE_INFO)
