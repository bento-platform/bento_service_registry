import datetime
import os
import sqlite3
import uuid

from flask import Flask, g, json

application = Flask(__name__)
application.config.from_mapping(
    CHORD_SERVICES=os.environ.get("CHORD_SERVICES", ""),
    DATABASE=os.environ.get("DATABASE", "chord_service_registry.db")
)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(application.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db():
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    c = db.cursor()

    with application.open_resource("schema.sql") as sf:
        db.executescript(sf.read())

        with application.open_resource(application.config["CHORD_SERVICES"]) as cf:
            sl = json.load(cf)
            for s in sl:
                r_id = uuid.uuid4()
                creation_time = datetime.datetime.utcnow().isoformat("T") + "Z"
                c.execute(
                    "INSERT INTO services VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %i)",
                    (r_id,           # UUID
                     s["id"],        # Service Name TODO: Get from /service-info
                     "TODO",         # URL TODO: Figure out how to get this
                     "TODO",         # Service Type TODO: Get from /service-info
                     creation_time,  # Created At
                     creation_time,  # Updated At
                     "TODO",         # Contact URL TODO: Where to get this from?
                     "TODO",         # Description TODO: Get from /service-info
                     s["id"],        # Chord ID (unique within an instance)
                     1 if s["data_service"] else 0)  # Boolean (is it a data service)?
                )

    db.commit()


# TODO: NEED TO BE ABLE TO UPDATE THE DATABASE

application.teardown_appcontext(close_db)

if not os.path.exists(application.config["DATABASE"]):
    init_db()


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
            "chordDataService": s["chord_data_service"]
        },
        "aliases": []
    }


@application.route("/services")
def services():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM services")
    return [format_service(s) for s in c.fetchall()]


@application.route("/services/<uuid:service_id>")
def service_by_id(service_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM services WHERE id = %s", (service_id,))

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
    return [t[0] for t in c.fetchall()]
