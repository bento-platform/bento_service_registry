import aiofiles
import aiohttp
import asyncio
import json
import logging

from bento_lib.types import GA4GHServiceInfo
from bento_service_registry import __version__
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, status
from json.decoder import JSONDecodeError
from urllib.parse import urljoin

from .authz import authz_middleware
from .config import Config, ConfigDependency
from .constants import BENTO_SERVICE_KIND, SERVICE_NAME, SERVICE_TYPE, SERVICE_ARTIFACT
from .logger import LoggerDependency
from .types import BentoService

__all__ = [
    "service_registry",
]

service_registry = APIRouter()


async def get_bento_services_by_compose_id(config: Config, logger: logging.Logger) -> dict[str, BentoService]:
    """
    Reads the list of services from the chord_services.json file
    """

    # Load bento_services.json data from the filesystem
    try:
        async with aiofiles.open(config.bento_services, "r") as f:
            # Return dictionary of services (id: configuration) Skip disabled services
            bento_services_data: dict[str, BentoService] = json.loads(await f.read())
    except Exception as e:
        except_name = type(e).__name__
        logger.error(f"Error retrieving information from bento_services JSON file: {except_name}")
        return {}

    return {
        sk: BentoService(
            **sv,
            url=sv["url_template"].format(
                BENTO_URL=config.bento_url,
                BENTO_PUBLIC_URL=config.bento_public_url,
                BENTO_PORTAL_PUBLIC_URL=config.bento_portal_public_url,
                **sv,
            ),
        )  # type: ignore
        for sk, sv in bento_services_data.items()
        # Filter out disabled entries and entries without service_kind, which may be external/'transparent'
        # - e.g., the gateway.
        if not sv.get("disabled") and sv.get("service_kind")
    }


async def get_bento_services_by_kind(config: Config, logger: logging.Logger) -> dict[str, BentoService]:
    services_by_kind: dict[str, BentoService] = {}

    for sv in (await get_bento_services_by_compose_id(config, logger)).values():
        # Disabled entries are already filtered out by get_bento_services_by_compose_id
        # Filter out entries without service_kind, which may be external/'transparent' - e.g., the gateway.
        if sk := sv.get("service_kind"):
            services_by_kind[sk] = sv

    return services_by_kind


async def get_service_url(config: Config, logger: logging.Logger, service_kind: str) -> str:
    return (await get_bento_services_by_kind(config, logger))[service_kind]["url"]


async def get_service(
    config: Config,
    logger: logging.Logger,
    request: Request,
    session: aiohttp.ClientSession,
    service_metadata: BentoService,
) -> dict[str, dict] | None:
    kind = service_metadata["service_kind"]

    # special case: requesting info about the current service. Skip networking / self-connect.
    if kind == BENTO_SERVICE_KIND:
        return await get_service_info(config, logger)

    timeout = aiohttp.ClientTimeout(total=config.contact_timeout)

    s_url: str = service_metadata["url"]
    service_info_url: str = urljoin(f"{s_url}/", "service-info")

    # Optional Authorization HTTP header to forward to nested requests
    # TODO: Move X-Auth... constant to bento_lib
    auth_header: str = request.headers.get("X-Authorization", request.headers.get("Authorization", ""))
    headers = {"Authorization": auth_header} if auth_header else {}

    dt = datetime.now()
    logger.info(f"Contacting {service_info_url}{' with bearer token' if auth_header else ''}")

    service_resp: dict[str, dict] = {}

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


@service_registry.get("/bento-services", dependencies=[authz_middleware.dep_public_endpoint()])
async def bento_services(config: ConfigDependency, logger: LoggerDependency):
    return await get_bento_services_by_compose_id(config, logger)


async def get_services(config: Config, logger: logging.Logger, request: Request) -> list[dict]:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.bento_validate_ssl)) as session:
        # noinspection PyTypeChecker
        service_list: list[dict | None] = await asyncio.gather(*[
            get_service(config, logger, request, session, s)
            for s in (await get_bento_services_by_compose_id(config, logger)).values()
        ])
        return [s for s in service_list if s is not None]


@service_registry.get("/services", dependencies=[authz_middleware.dep_public_endpoint()])
async def services(config: ConfigDependency, logger: LoggerDependency, request: Request):
    return await get_services(config, logger, request)


@service_registry.get("/services/types", dependencies=[authz_middleware.dep_public_endpoint()])
async def service_types(config: ConfigDependency, logger: LoggerDependency, request: Request) -> list[dict]:
    types_by_key: dict[str, dict] = {}
    for st in (s["type"] for s in await get_services(config, logger, request)):
        sk = ":".join(st.values())
        types_by_key[sk] = st

    return list(types_by_key.values())


@service_registry.get("/services/{service_id}", dependencies=[authz_middleware.dep_public_endpoint()])
async def service_by_id(
    config: ConfigDependency,
    logger: LoggerDependency,
    request: Request,
    service_id: str,
):
    services_by_id = {s["id"]: s for s in (await get_services(config, logger, request))}
    bento_services_by_kind = await get_bento_services_by_kind(config, logger)

    if service_id not in services_by_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Service with ID {service_id} was not found in registry")

    svc = services_by_id[service_id]

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=config.bento_validate_ssl)) as session:
        # Get service by bento.serviceKind, using type.artifact as a backup for legacy reasons
        service_data = await get_service(
            config,
            logger,
            request,
            session,
            bento_services_by_kind[svc.get("bento", {}).get("serviceKind", svc["type"]["artifact"])],
        )

        if service_data is None:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"An internal error was encountered with service with ID {service_id}")

        return service_data


async def _git_stdout(*args) -> str:
    git_proc = await asyncio.create_subprocess_exec(
        "git", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    res, _ = await git_proc.communicate()
    return res.decode().rstrip()


async def get_service_info(config: Config, logger: logging.Logger) -> GA4GHServiceInfo:
    service_id = config.service_id
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
        "url": await get_service_url(config, logger, SERVICE_ARTIFACT),
        "environment": "prod",
        "bento": {
            "serviceKind": BENTO_SERVICE_KIND,
        },
    }

    if not config.bento_debug:
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
        logger.error(f"Error in dev mode retrieving git information: {str(except_name)}")

    return service_info_dict  # updated service info with the git info


@service_registry.get("/service-info", dependencies=[authz_middleware.dep_public_endpoint()])
async def service_info(config: ConfigDependency, logger: LoggerDependency):
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info
    return await get_service_info(config, logger)
