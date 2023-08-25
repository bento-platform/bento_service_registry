import asyncio

from bento_lib.types import GA4GHServiceInfo
from bento_service_registry import __version__
from fastapi import Depends
from typing import Annotated

from .bento_services_json import BentoServicesByKindDependency
from .config import ConfigDependency
from .constants import BENTO_SERVICE_KIND, SERVICE_NAME, SERVICE_TYPE
from .logger import LoggerDependency
from .utils import get_service_url


__all__ = [
    "get_service_info",
    "ServiceInfoDependency",
]


async def _git_stdout(*args) -> str:
    git_proc = await asyncio.create_subprocess_exec(
        "git", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    res, _ = await git_proc.communicate()
    return res.decode().rstrip()


async def get_service_info(
    bento_services_by_kind: BentoServicesByKindDependency,
    config: ConfigDependency,
    logger: LoggerDependency,
) -> GA4GHServiceInfo:
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
        "url": get_service_url(bento_services_by_kind, BENTO_SERVICE_KIND),
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


ServiceInfoDependency = Annotated[GA4GHServiceInfo, Depends(get_service_info)]
