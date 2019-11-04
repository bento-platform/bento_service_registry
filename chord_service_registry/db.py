import datetime
import json
import os
import sqlite3
import uuid

from flask import current_app, g
from typing import Dict


__all__ = ["get_db", "close_db", "init_db", "update_db"]


def insert_service_record(c: sqlite3.Cursor, s: Dict):
    r_id = str(uuid.uuid4())
    creation_time = datetime.datetime.utcnow().isoformat("T") + "Z"

    c.execute(
        "INSERT INTO services VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (r_id,  # UUID
         s["id"],  # Service Name TODO: Get from /service-info
         f"/{s['id']}",  # URL TODO: Figure out how to get this
         "TODO",  # Service Type TODO: Get from /service-info
         creation_time,  # Created At
         creation_time,  # Updated At
         "TODO",  # Contact URL TODO: Where to get this from?
         "TODO",  # Description TODO: Get from /service-info
         s["id"],  # Chord ID (unique within an instance)
         int(s["data_service"]),  # Boolean (is it a data service)?
         int(s.get("manageable_tables", False)))  # Boolean (does it have user-manageable tables)?
    )

    return r_id


def update_service_record(c: sqlite3.Cursor, s: Dict):
    if "id" not in s:
        return

    # TODO: Update more fields

    c.execute("UPDATE services SET chord_data_service = ?, chord_manageable_tables = ? WHERE name = ?",
              (int(s["data_service"]), int(s.get("manageable_tables", False)), s["id"]))


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    c = db.cursor()

    with current_app.open_resource("schema.sql") as sf:
        db.executescript(sf.read().decode("utf-8"))

        with open(os.path.join(os.getcwd(), current_app.config["CHORD_SERVICES"]), "r") as cf:
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

    with open(os.path.join(os.getcwd(), current_app.config["CHORD_SERVICES"]), "r") as cf:
        sl = json.load(cf)
        service_ids = []

        for s in sl:
            c.execute("SELECT * FROM services WHERE chord_service_id = ?", (s["id"],))
            existing_service = c.fetchone()
            if existing_service is None:
                # Create a new service record, since the service is not in the database.
                service_ids.append(insert_service_record(c, s))
            else:
                # Update existing record with possibly-updated data.
                update_service_record(c, s)
                service_ids.append(existing_service["id"])

        # Delete old services that are no longer in the chord_services.json file.
        c.execute("DELETE FROM services WHERE id NOT IN ({})".format(", ".join(["?"] * len(service_ids))),
                  tuple(service_ids))

    db.commit()
