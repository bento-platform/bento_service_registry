import chord_service_registry
import datetime
import os
import sqlite3
import uuid

from flask import Flask, g, json, jsonify
from typing import Dict

application = Flask(__name__)
application.config.from_mapping(
    CHORD_SERVICES=os.environ.get("CHORD_SERVICES", "chord_services.json"),
    DATABASE=os.environ.get("DATABASE", "chord_service_registry.db")
)


def insert_service_record(c: sqlite3.Cursor, s: Dict):
    r_id = str(uuid.uuid4())
    creation_time = datetime.datetime.utcnow().isoformat("T") + "Z"

    c.execute(
        "INSERT INTO services VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (r_id,  # UUID
         s["id"],  # Service Name TODO: Get from /service-info
         f"/{s['id']}",  # URL TODO: Figure out how to get this
         "TODO",  # Service Type TODO: Get from /service-info
         creation_time,  # Created At
         creation_time,  # Updated At
         "TODO",  # Contact URL TODO: Where to get this from?
         "TODO",  # Description TODO: Get from /service-info
         s["id"],  # Chord ID (unique within an instance)
         1 if s["data_service"] else 0)  # Boolean (is it a data service)?
    )

    return r_id


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(application.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    c = db.cursor()

    with application.open_resource("schema.sql") as sf:
        db.executescript(sf.read().decode("utf-8"))

        with open(os.path.join(os.getcwd(), application.config["CHORD_SERVICES"]), "r") as cf:
            sl = json.load(cf)
            for s in sl:
                insert_service_record(c, s)

    db.commit()


def update_db():
    db = get_db()
    c = db.cursor()

    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='services'")
    if c.fetchone() is None:
        init_db()
        return

    with open(os.path.join(os.getcwd(), application.config["CHORD_SERVICES"]), "r") as cf:
        sl = json.load(cf)
        service_ids = []

        for s in sl:
            c.execute("SELECT * FROM services WHERE chord_service_id = ?", (s["id"],))
            existing_service = c.fetchone()
            if existing_service is None:
                # Create a new service record, since the service is not in the database.
                service_ids.append(insert_service_record(c, s))
            else:
                # TODO: May want to update service data
                service_ids.append(existing_service["id"])

        # Delete old services that are no longer in the chord_services.json file.
        c.execute("DELETE FROM services WHERE id NOT IN ({})".format(", ".join(["?"] * len(service_ids))),
                  tuple(service_ids))

    db.commit()


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
            "chordServiceID": s["chord_service_id"] == 1,
            "chordDataService": s["chord_data_service"]
        },
        "aliases": []
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
        "type": "urn:ga4gh:service-registry",
        "description": "Service registry for a CHORD application.",
        "organization": "GenAP",
        "contactUrl": "mailto:david.lougheed@mail.mcgill.ca",
        "version": chord_service_registry.__version__,
        "extension": {}
    })
