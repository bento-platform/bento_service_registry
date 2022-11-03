from __future__ import annotations

import aiofiles
import aiohttp
import asyncio
import bento_service_registry
import os
import sys
import subprocess

from bento_lib.responses.flask_errors import (
    flask_error_wrap,
    flask_error_wrap_with_traceback,
    flask_internal_server_error,
    flask_bad_request_error,
    flask_not_found_error,
)
from quart import Quart, current_app, json, request
from json.decoder import JSONDecodeError
from typing import Optional
from urllib.parse import urljoin
from werkzeug.exceptions import BadRequest, NotFound


SERVICE_ARTIFACT = "service-registry"

# For exact implementations, this should be org.ga4gh/service-registry/1.0.0.
# In our case, most of our services diverge or will at some point, so use ca.c3g.bento as the group.
SERVICE_TYPE = {
    "group": "ca.c3g.bento",
    "artifact": SERVICE_ARTIFACT,
    "version": bento_service_registry.__version__,
}
SERVICE_NAME = "Bento Service Registry"


application = Quart(__name__)
application.config.from_mapping(
    BENTO_DEBUG=os.environ.get("CHORD_DEBUG", os.environ.get("QUART_ENV", "production")).strip().lower() in (
        "true", "1", "development"),
    CHORD_SERVICES=os.environ.get("CHORD_SERVICES", os.environ.get("BENTO_SERVICES", "chord_services.json")),
    CHORD_URL=os.environ.get("CHORD_URL", os.environ.get("BENTO_URL", "http://127.0.0.1:5000/")),  # Own node's URL
    CONTACT_TIMEOUT=int(os.environ.get("CONTACT_TIMEOUT", 1)),
    SERVICE_ID=os.environ.get("SERVICE_ID", ":".join(SERVICE_TYPE.values())),
    URL_PATH_FORMAT=os.environ.get("URL_PATH_FORMAT", "api/{artifact}"),
)

path_for_git = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# TODO: Quart errors
# Generic catch-all
# application.register_error_handler(Exception, flask_error_wrap_with_traceback(flask_internal_server_error,
#                                                                               sr_compat=True,
#                                                                               service_name=SERVICE_NAME))
# application.register_error_handler(BadRequest, flask_error_wrap(flask_bad_request_error, sr_compat=True))
# application.register_error_handler(NotFound, flask_error_wrap(flask_not_found_error, sr_compat=True))


def get_service_url(artifact: str) -> str:
    return urljoin(current_app.config["CHORD_URL"], current_app.config["URL_PATH_FORMAT"].format(artifact=artifact))


async def get_chord_services() -> list[dict]:
    """
    Reads the list of services from the chord_services.json file
    """
    try:
        async with aiofiles.open(current_app.config["CHORD_SERVICES"], "r") as f:
            return [s for s in json.loads(await f.read()) if not s.get("disabled")]  # Skip disabled services
    except Exception as e:
        except_name = type(e).__name__
        print("Error in retrieving services information from json file.", except_name)
    finally:
        return []


async def get_service(session: aiohttp.ClientSession, service_artifact: str) -> Optional[dict[str, dict]]:
    # special case: requesting info about the current service. Avoids request timeout
    # when running gunicorn on a single worker
    if service_artifact == SERVICE_ARTIFACT:
        return await get_service_info()

    s_url: str = get_service_url(service_artifact)
    service_info_url: str = urljoin(f"{s_url}/", "service-info")

    print(f"[{SERVICE_NAME}] Contacting {service_info_url}", flush=True)

    # Optional Authorization HTTP header to forward to nested requests
    # TODO: Move X-Auth... constant to bento_lib
    auth_header: str = request.headers.get("X-Authorization", request.headers.get("Authorization", ""))
    headers = {"Authorization": auth_header} if auth_header else {}

    service_resp: dict[str, dict] = {}

    try:
        async with session.get(service_info_url, headers=headers, ssl=not current_app.config["BENTO_DEBUG"]) as r:
            if r.status != 200:
                r_text = await r.text()
                print(f"[{SERVICE_NAME}] Non-200 status code on {service_artifact}: {r.status}\n"
                      f"                 Content: {r_text}", file=sys.stderr, flush=True)

                # If we have the special case where we got a JWT error from the proxy script, we can safely print out
                # headers for debugging, since the JWT leaked isn't valid anyway.
                if "invalid jwt" in r_text:
                    print(f"                 Encountered auth error, tried to use header: {auth_header}",
                          file=sys.stderr, flush=True)

                return None

    except aiohttp.ServerTimeoutError:
        print(f"[{SERVICE_NAME}] Encountered timeout with {service_info_url}", file=sys.stderr, flush=True)
        return None

    try:
        service_resp[service_artifact] = {**(await r.json()), "url": s_url}
    except JSONDecodeError:
        print(f"[{SERVICE_NAME}] Encountered invalid response from {service_info_url}: {await r.text()}")
        return None

    return service_resp[service_artifact]


@application.before_first_request
async def before_first_request_func() -> None:
    try:
        # TODO: asyncify
        subprocess.run(["git", "config", "--global", "--add", "safe.directory", str(path_for_git)])
    except Exception as e:
        except_name = type(e).__name__
        print("Error in dev-mode retrieving git folder configuration", except_name)


@application.route("/bento-services")
@application.route("/chord-services")
async def chord_services():
    return json.jsonify(await get_chord_services())


async def get_services() -> list[dict]:
    timeout = aiohttp.ClientTimeout(total=current_app.config["CONTACT_TIMEOUT"])
    async with aiohttp.ClientSession(timeout=timeout) as session:
        return [s for s in asyncio.gather(*[
            get_service(session, s["type"]["artifact"])
            for s in (await get_chord_services())
        ]) if s is not None]


@application.route("/services")
async def services():
    return json.jsonify(await get_services())


@application.route("/services/<string:service_id>")
async def service_by_id(service_id: str):
    services_by_id = {s["id"]: s for s in (await get_services())}
    if service_id not in services_by_id:
        return flask_not_found_error(f"Service with ID {service_id} was not found in registry")

    service_artifact = services_by_id[service_id]["type"].split(":")[1]

    timeout = aiohttp.ClientTimeout(total=current_app.config["CONTACT_TIMEOUT"])
    async with aiohttp.ClientSession(timeout=timeout) as session:
        return get_service(session, service_artifact)


@application.route("/services/types")
async def service_types():
    return json.jsonify(sorted(set(s["type"] for s in await get_services())))


async def get_service_info() -> dict:
    service_id = current_app.config["SERVICE_ID"]
    service_info_dict = {
        "id": service_id,
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

    if not current_app.config["BENTO_DEBUG"]:
        return service_info_dict

    info = {
        **service_info_dict,
        "environment": "dev"
    }
    try:
        git_proc = await asyncio.create_subprocess_exec(
            "git", "describe", "--tags", "--abbrev=0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        res_tag, _ = await git_proc.communicate()
        if res_tag:
            info["git_tag"] = res_tag.decode().rstrip()

        git_proc = await asyncio.create_subprocess_exec(
            "git", "branch", "--show-current",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        res_branch, _ = await git_proc.communicate()
        if res_branch:
            info["git_branch"] = res_branch.decode().rstrip()

    except Exception as e:
        except_name = type(e).__name__
        print("Error in dev-mode retrieving git information", except_name)

    return info  # updated service info with the git info


@application.route("/service-info")
async def service_info():
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info
    return json.jsonify(await get_service_info())
