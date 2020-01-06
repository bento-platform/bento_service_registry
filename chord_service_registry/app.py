import chord_service_registry
import datetime
import os
import requests
import sys

from flask import Flask, json, jsonify
from urllib.parse import urljoin


TIMEOUT = 1


SERVICE_ARTIFACT = "service-registry"
SERVICE_TYPE = f"ca.c3g.chord:{SERVICE_ARTIFACT}:{chord_service_registry.__version__}"
SERVICE_ID = os.environ.get("SERVICE_ID", SERVICE_TYPE)

SERVICE_INFO = {
    "id": SERVICE_ID,
    "name": "CHORD Service Registry",  # TODO: Should be globally unique?
    "type": SERVICE_TYPE,
    "description": "Service registry for a CHORD application.",
    "organization": {
        "name": "C3G",
        "url": "http://www.computationalgenomics.ca"
    },
    "contactUrl": "mailto:david.lougheed@mail.mcgill.ca",
    "version": chord_service_registry.__version__
}

URL_PATH_FORMAT = os.environ.get("URL_PATH_FORMAT", "/api/{artifact}")

CHORD_URL = os.environ.get("CHORD_URL", "http://127.0.0.1:5000/")  # Own node's URL
CHORD_SERVICES_PATH = os.environ.get("CHORD_SERVICES", "chord_services.json")
CHORD_SERVICES = json.load(open(CHORD_SERVICES_PATH, "r"))


application = Flask(__name__)
application.config.from_mapping(CHORD_SERVICES=CHORD_SERVICES_PATH)


service_info_cache = {}


def get_service(s):
    s_artifact = s["type"]["artifact"]
    s_url = urljoin(CHORD_URL, URL_PATH_FORMAT.format(artifact=s_artifact))

    if s_artifact not in service_info_cache:
        if s_artifact == SERVICE_ARTIFACT:
            service_info_cache[s_artifact] = {**SERVICE_INFO, "url": s_url}
        else:
            print(urljoin(s_url + "/", "service-info"))

            try:
                r = requests.get(urljoin(s_url + "/", "service-info"), timeout=TIMEOUT)
                if r.status_code != 200:
                    print("Non-200 status code on {}: {}".format(s_artifact, r.status_code), file=sys.stderr)
                    return None
            except requests.exceptions.Timeout:
                print("Timeout on {}".format(s_artifact), file=sys.stderr)
                return None

            service_info_cache[s_artifact] = {**r.json(), "url": s_url}

    return service_info_cache[s_artifact]


@application.route("/chord-services")
def chord_services():
    return jsonify(CHORD_SERVICES)


@application.route("/services")
def services():
    service_list = [get_service(s) for s in CHORD_SERVICES]
    return jsonify([s for s in service_list if s is not None])


@application.route("/services/<string:service_id>")
def service_by_id(service_id):
    services_by_id = {s["id"]: s for s in service_info_cache.values()}
    if service_id not in service_by_id:
        return jsonify({
            "code": 404,
            "message": "Service not found",
            "timestamp": datetime.datetime.utcnow().isoformat("T") + "Z",
            "errors": [{"code": "not_found", "message": f"Service with ID {service_id} was not found in registry"}]
        }), 404

    return get_service(services_by_id[service_id])


@application.route("/services/types")
def service_types():
    return jsonify(sorted(set(s["type"] for s in service_info_cache.values())))


@application.route("/service-info")
def service_info():
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info
    return jsonify(SERVICE_INFO)
