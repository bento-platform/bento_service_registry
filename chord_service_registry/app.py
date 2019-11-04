import chord_service_registry
import datetime
import os

from flask import Flask, json, jsonify

from .db import *

application = Flask(__name__)
application.config.from_mapping(
    CHORD_SERVICES=os.environ.get("CHORD_SERVICES", "chord_services.json"),
    DATABASE=os.environ.get("DATABASE", "chord_service_registry.db")
)


# TODO: NEED TO BE ABLE TO UPDATE THE DATABASE

application.teardown_appcontext(close_db)

with application.app_context():
    if not os.path.exists(os.path.join(os.getcwd(), application.config["DATABASE"])):
        init_db()
    else:
        update_db()


def format_service(s):
    return {
        "id": s["id"],
        "name": s["name"],
        "url": s["url"],
        "type": s["service_type"],
        "createdAt": s["created_at"],
        "updatedAt": s["updated_at"],
        "contactUrl": s["contact_url"],
        "description": s["description"],
        "metadata": {
            "chordServiceID": s["chord_service_id"],
            "chordDataService": s["chord_data_service"] == 1,
            "chordManageableTables": s["chord_manageable_tables"] == 1
        }
    }


@application.route("/services")
def services():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM services")
    return jsonify([format_service(s) for s in c.fetchall()])


@application.route("/services/<uuid:service_id>")
def service_by_id(service_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM services WHERE id = ?", (str(service_id),))

    service = c.fetchone()
    if service is None:
        return application.response_class(
            response=json.dumps({
                "code": 404,
                "message": "Service not found",
                "timestamp": datetime.datetime.utcnow().isoformat("T") + "Z",
                "errors": [{"code": "not_found", "message": f"Service with ID {service_id} was not found in registry"}]
            })
        )

    return format_service(service)


@application.route("/services/types")
def service_types():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT DISTINCT service_type FROM services")
    return jsonify([t[0] for t in c.fetchall()])


@application.route("/service-info")
def service_info():
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info

    return jsonify({
        "id": "ca.distributedgenomics.chord_service_registry",  # TODO: Should be globally unique
        "name": "CHORD Service Registry",                       # TODO: Should be globally unique
        "type": "org.ga4gh:service-registry:0.0.0",
        "description": "Service registry for a CHORD application.",
        "organization": {
            "name": "GenAP",
            "url": "https://genap.ca/"
        },
        "contactUrl": "mailto:david.lougheed@mail.mcgill.ca",
        "version": chord_service_registry.__version__
    })
