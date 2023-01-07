from __future__ import annotations

import aiofiles
import aiohttp
import asyncio
import sys

from bento_lib.responses.quart_errors import quart_not_found_error
from bento_lib.types import GA4GHServiceInfo
from bento_service_registry import __version__
from datetime import datetime
from json.decoder import JSONDecodeError
from quart import Blueprint, current_app, json, request
from typing import Optional
from urllib.parse import urljoin

from .constants import SERVICE_NAME, SERVICE_TYPE, SERVICE_ARTIFACT

service_registry = Blueprint("service_registry", __name__)


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
        print("Error retrieving information from chord_services JSON file:", except_name)
        return []


async def get_service(session: aiohttp.ClientSession, service_artifact: str) -> Optional[dict[str, dict]]:
    # special case: requesting info about the current service. Skip networking / self-connect.
    if service_artifact == SERVICE_ARTIFACT:
        return await get_service_info()

    timeout = aiohttp.ClientTimeout(total=current_app.config["CONTACT_TIMEOUT"])

    s_url: str = get_service_url(service_artifact)
    service_info_url: str = urljoin(f"{s_url}/", "service-info")

    # Optional Authorization HTTP header to forward to nested requests
    # TODO: Move X-Auth... constant to bento_lib
    auth_header: str = request.headers.get("X-Authorization", request.headers.get("Authorization", ""))
    headers = {"Authorization": auth_header} if auth_header else {}

    dt = datetime.now()
    print(f"[{SERVICE_NAME}] Contacting {service_info_url}{' with bearer token' if auth_header else ''}", flush=True)

    service_resp: dict[str, dict] = {}

    try:
        async with session.get(service_info_url, headers=headers, timeout=timeout) as r:
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

            try:
                service_resp[service_artifact] = {**(await r.json()), "url": s_url}
            except JSONDecodeError:
                print(f"[{SERVICE_NAME}] Encountered invalid response from {service_info_url}: {await r.text()}")

            print(f"[{SERVICE_NAME}] {service_info_url}: Took {(datetime.now() - dt).total_seconds():.1f}s", flush=True)

    except asyncio.TimeoutError:
        print(f"[{SERVICE_NAME}] Encountered timeout with {service_info_url}", file=sys.stderr, flush=True)

    except aiohttp.ClientConnectionError as e:
        print(f"[{SERVICE_NAME}] Encountered connection error with {service_info_url}: {str(e)}",
              file=sys.stderr, flush=True)

    return service_resp.get(service_artifact)


@service_registry.route("/bento-services")
@service_registry.route("/chord-services")
async def chord_services():
    return json.jsonify(await get_chord_services())


async def get_services() -> list[dict]:
    async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=current_app.config["BENTO_VALIDATE_SSL"])) as session:
        # noinspection PyTypeChecker
        service_list: list[Optional[dict]] = await asyncio.gather(*[
            get_service(session, s["type"]["artifact"])
            for s in (await get_chord_services())
        ])
        return [s for s in service_list if s is not None]


@service_registry.route("/services")
async def services():
    return json.jsonify(await get_services())


@service_registry.route("/services/<string:service_id>")
async def service_by_id(service_id: str):
    services_by_id = {s["id"]: s for s in (await get_services())}
    if service_id not in services_by_id:
        return quart_not_found_error(f"Service with ID {service_id} was not found in registry")

    async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=current_app.config["BENTO_VALIDATE_SSL"])) as session:
        return await get_service(session, services_by_id[service_id]["type"]["artifact"])


@service_registry.route("/services/types")
async def service_types():
    types_by_key: dict[str, dict] = {}
    for st in (s["type"] for s in await get_services()):
        sk = ":".join(st.values())
        types_by_key[sk] = st

    return json.jsonify(list(types_by_key.values()))


async def get_service_info() -> GA4GHServiceInfo:
    service_id = current_app.config["SERVICE_ID"]
    service_info_dict: GA4GHServiceInfo = {
        "id": service_id,
        "name": SERVICE_NAME,  # TODO: Should be globally unique?
        "type": SERVICE_TYPE,
        "description": "Service registry for a Bento platform node.",
        "organization": {
            "name": "C3G",
            "url": "https://www.computationalgenomics.ca"
        },
        "contactUrl": "mailto:info@c3g.ca",
        "version": __version__,
        "url": get_service_url(SERVICE_ARTIFACT),
        "environment": "prod"
    }

    if not current_app.config["BENTO_DEBUG"]:
        return service_info_dict

    service_info_dict["environment"] = "dev"

    try:
        git_proc = await asyncio.create_subprocess_exec(
            "git", "describe", "--tags", "--abbrev=0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        res_tag, _ = await git_proc.communicate()
        if res_tag:
            service_info_dict["git_tag"] = res_tag.decode().rstrip()

        git_proc = await asyncio.create_subprocess_exec(
            "git", "branch", "--show-current",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        res_branch, _ = await git_proc.communicate()
        if res_branch:
            service_info_dict["git_branch"] = res_branch.decode().rstrip()

    except Exception as e:
        except_name = type(e).__name__
        print("Error in dev-mode retrieving git information", except_name)

    return service_info_dict  # updated service info with the git info


@service_registry.route("/service-info")
async def service_info():
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info
    return json.jsonify(await get_service_info())
