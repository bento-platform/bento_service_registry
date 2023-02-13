import aiofiles
import aiohttp
import asyncio
import sys

import quart
from bento_lib.responses.quart_errors import quart_not_found_error, quart_internal_server_error
from bento_lib.types import GA4GHServiceInfo
from bento_service_registry import __version__
from datetime import datetime
from json.decoder import JSONDecodeError
from quart import Blueprint, current_app, json, request
from typing import Dict, List, Optional, Union
from urllib.parse import urljoin

from .constants import BENTO_SERVICE_KIND, SERVICE_NAME, SERVICE_TYPE, SERVICE_ARTIFACT
from .types import BentoService

service_registry = Blueprint("service_registry", __name__)


async def get_bento_services_by_compose_id() -> Dict[str, BentoService]:
    """
    Reads the list of services from the chord_services.json file
    """

    # Load bento_services.json data from the filesystem
    try:
        async with aiofiles.open(current_app.config["BENTO_SERVICES"], "r") as f:
            # Return dictionary of services (id: configuration) Skip disabled services
            chord_services_data: Dict[str, BentoService] = json.loads(await f.read())
    except Exception as e:
        except_name = type(e).__name__
        print("Error retrieving information from chord_services JSON file:", except_name, file=sys.stderr)
        return {}

    return {
        sk: BentoService(
            **sv,
            url=sv["url_template"].format(
                BENTO_URL=current_app.config["BENTO_URL"],
                BENTO_PUBLIC_URL=current_app.config["BENTO_PUBLIC_URL"],
                BENTO_PORTAL_PUBLIC_URL=current_app.config["BENTO_PORTAL_PUBLIC_URL"],
                **sv,
            ),
        )  # type: ignore
        for sk, sv in chord_services_data.items()
        # Filter out disabled entries and entries without service_kind, which may be external/'transparent'
        # - e.g., the gateway.
        if not sv.get("disabled") and sv.get("service_kind")
    }


async def get_bento_services_by_kind() -> Dict[str, BentoService]:
    services_by_kind: Dict[str, BentoService] = {}

    for sv in (await get_bento_services_by_compose_id()).values():
        # Disabled entries are already filtered out by get_bento_services_by_compose_id
        # Filter out entries without service_kind, which may be external/'transparent' - e.g., the gateway.
        if sk := sv.get("service_kind"):
            services_by_kind[sk] = sv

    return services_by_kind


async def get_service_url(service_kind: str) -> str:
    return (await get_bento_services_by_kind())[service_kind]["url"]


async def get_service(session: aiohttp.ClientSession, service_metadata: BentoService) -> Optional[Dict[str, dict]]:
    logger = current_app.logger

    kind = service_metadata["service_kind"]

    # special case: requesting info about the current service. Skip networking / self-connect.
    if kind == BENTO_SERVICE_KIND:
        return await get_service_info()

    timeout = aiohttp.ClientTimeout(total=current_app.config["CONTACT_TIMEOUT"])

    s_url: str = service_metadata["url"]
    service_info_url: str = urljoin(f"{s_url}/", "service-info")

    # Optional Authorization HTTP header to forward to nested requests
    # TODO: Move X-Auth... constant to bento_lib
    auth_header: str = request.headers.get("X-Authorization", request.headers.get("Authorization", ""))
    headers = {"Authorization": auth_header} if auth_header else {}

    dt = datetime.now()
    logger.info(f"Contacting {service_info_url}{' with bearer token' if auth_header else ''}")

    service_resp: Dict[str, dict] = {}

    try:
        async with session.get(service_info_url, headers=headers, timeout=timeout) as r:
            if r.status != 200:
                r_text = await r.text()
                logger.error(f"Non-200 status code on {kind}: {r.status}  Content: {r_text}")

                # If we have the special case where we got a JWT error from the proxy script, we can safely print out
                # headers for debugging, since the JWT leaked isn't valid anyway.
                if "invalid jwt" in r_text:
                    logger.error(f"Encountered auth error on {kind}; tried to use header: {auth_header}")

                return None

            try:
                service_resp[kind] = {**(await r.json()), "url": s_url}
            except (JSONDecodeError, aiohttp.ContentTypeError, TypeError) as e:
                # JSONDecodeError can happen if the JSON is invalid
                # ContentTypeError can happen if the Content-Type is not application/json
                # TypeError can happen if None is received
                logger.error(f"Encountered invalid response ({str(e)}) from {service_info_url}: {await r.text()}")

            logger.info(f"{service_info_url}: Took {(datetime.now() - dt).total_seconds():.1f}s")

    except asyncio.TimeoutError:
        logger.error(f"Encountered timeout with {service_info_url}")

    except aiohttp.ClientConnectionError as e:
        logger.error(f"Encountered connection error with {service_info_url}: {str(e)}")

    return service_resp.get(kind)


@service_registry.route("/bento-services")
@service_registry.route("/chord-services")
async def chord_services():
    return json.jsonify(await get_bento_services_by_compose_id())


async def get_services() -> List[dict]:
    async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=current_app.config["BENTO_VALIDATE_SSL"])) as session:
        # noinspection PyTypeChecker
        service_list: List[Optional[dict]] = await asyncio.gather(*[
            get_service(session, s)
            for s in (await get_bento_services_by_compose_id()).values()
        ])
        return [s for s in service_list if s is not None]


@service_registry.route("/services")
async def services():
    return json.jsonify(await get_services())


@service_registry.route("/services/<string:service_id>")
async def service_by_id(service_id: str) -> Union[quart.Response, dict]:
    services_by_id = {s["id"]: s for s in (await get_services())}
    chord_services_by_kind = await get_bento_services_by_kind()

    if service_id not in services_by_id:
        return quart_not_found_error(f"Service with ID {service_id} was not found in registry")

    svc = services_by_id[service_id]

    async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=current_app.config["BENTO_VALIDATE_SSL"])) as session:
        # Get service by bento.serviceKind, using type.artifact as a backup for legacy reasons
        service_data = await get_service(
            session, chord_services_by_kind[svc.get("bento", {}).get("serviceKind", svc["type"]["artifact"])])

        if service_data is None:
            return quart_internal_server_error(f"An internal error was encountered with service with ID {service_id}")

        return service_data


@service_registry.route("/services/types")
async def service_types() -> quart.Response:
    types_by_key: Dict[str, dict] = {}
    for st in (s["type"] for s in await get_services()):
        sk = ":".join(st.values())
        types_by_key[sk] = st

    return json.jsonify(list(types_by_key.values()))


async def _git_stdout(*args) -> str:
    git_proc = await asyncio.create_subprocess_exec(
        "git", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    res, _ = await git_proc.communicate()
    return res.decode().rstrip()


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
        "url": await get_service_url(SERVICE_ARTIFACT),
        "environment": "prod",
        "bento": {
            "serviceKind": BENTO_SERVICE_KIND,
        },
    }

    if not current_app.config["BENTO_DEBUG"]:
        return service_info_dict

    service_info_dict["environment"] = "dev"

    try:
        if res_tag := await _git_stdout("describe", "--tags", "--abbrev=0"):
            # noinspection PyTypeChecker
            service_info_dict["bento"]["gitTag"] = res_tag
        if res_branch := await _git_stdout("branch", "--show-current"):
            # noinspection PyTypeChecker
            service_info_dict["bento"]["gitBranch"] = res_branch
        if res_commit := await _git_stdout("rev-parse", "HEAD"):
            # noinspection PyTypeChecker
            service_info_dict["bento"]["gitCommit"] = res_commit

    except Exception as e:
        except_name = type(e).__name__
        current_app.logger.error(f"Error in dev mode retrieving git information: {str(except_name)}")

    return service_info_dict  # updated service info with the git info


@service_registry.route("/service-info")
async def service_info() -> quart.Response:
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info
    return json.jsonify(await get_service_info())
