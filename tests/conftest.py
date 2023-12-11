import logging
import os
import pytest
import pytest_asyncio

from fastapi.testclient import TestClient
from pathlib import Path

from bento_service_registry.config import Config

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
    from bento_service_registry.app import create_app
    app = create_app(tgc)
    yield TestClient(app)


@pytest.fixture()
def client_debug_mode():
    tgc = test_get_config(debug_mode=True)
    from bento_service_registry.app import create_app
    app = create_app(tgc)
    yield TestClient(app)


async def _service_info_fixt(config: Config):
    from bento_service_registry.service_info import get_service_info
    return await get_service_info(config, test_logger)


@pytest_asyncio.fixture()
async def service_info():
    tgc = test_get_config(debug_mode=False)
    yield _service_info_fixt(tgc())
