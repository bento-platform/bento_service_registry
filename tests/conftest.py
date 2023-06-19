import aiohttp
import logging
import os
import pytest
import pytest_asyncio

from fastapi.testclient import TestClient
from pathlib import Path

from bento_service_registry.config import Config, get_config

test_logger = logging.getLogger(__name__)


def test_get_config(debug_mode: bool):
    config_vars = dict(
        bento_url="http://0.0.0.0:5000/",
        bento_public_url="http://0.0.0.0:5000/",
        bento_portal_public_url="http://0.0.0.0:5000/",
        bento_services=Path(__file__).parent / "bento_services.json",
        bento_debug=debug_mode,
        cors_origins=["*"],
        bento_authz_service_url="http://bento-auth.local",
    )

    for k, v in config_vars.items():
        os.environ[k.upper()] = str(v) if not isinstance(v, list) else v[0]  # cors special case

    def get_config_inner():
        return Config(**config_vars)

    return get_config_inner


@pytest.fixture()
def client():
    tgc = test_get_config(debug_mode=False)
    from bento_service_registry.app import application
    application.dependency_overrides[get_config] = tgc
    yield TestClient(application)
    application.dependency_overrides = {}


@pytest.fixture()
def client_debug_mode():
    tgc = test_get_config(debug_mode=True)
    from bento_service_registry.app import application
    application.dependency_overrides[get_config] = tgc
    yield TestClient(application)
    application.dependency_overrides = {}


async def _service_info_fixt():
    from bento_service_registry.routes import get_service_info
    return await get_service_info(get_config(), test_logger)


@pytest_asyncio.fixture()
async def service_info():
    tgc = test_get_config(debug_mode=False)
    from bento_service_registry.app import application
    application.dependency_overrides[get_config] = tgc
    yield _service_info_fixt()
    application.dependency_overrides = {}


@pytest_asyncio.fixture()
async def aiohttp_session():
    tgc = test_get_config(debug_mode=False)
    from bento_service_registry.app import application
    application.dependency_overrides[get_config] = tgc
    async with aiohttp.ClientSession(timeout=1) as session:
        yield session
    application.dependency_overrides = {}
