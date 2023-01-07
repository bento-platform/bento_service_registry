import aiohttp
import os
import pytest
import pytest_asyncio


def _setup_env(debug_mode: bool = False):
    os.environ["CHORD_SERVICES"] = os.path.join(os.path.dirname(__file__), "chord_services.json")
    os.environ["URL_PATH_FORMAT"] = ""  # Mount off of root URL for testing
    os.environ["CHORD_DEBUG"] = "true" if debug_mode else ""


@pytest.fixture()
def client():
    _setup_env()
    from bento_service_registry.app import create_app
    yield create_app().test_client()


@pytest.fixture()
def client_debug_mode():
    _setup_env(debug_mode=True)
    from bento_service_registry.app import create_app
    yield create_app().test_client()


async def _service_info_fixt():
    from bento_service_registry.app import create_app
    from bento_service_registry.routes import get_service_info
    async with create_app().app_context():
        return await get_service_info()


@pytest_asyncio.fixture()
async def service_info():
    _setup_env()
    yield _service_info_fixt()


@pytest_asyncio.fixture()
async def aiohttp_session():
    _setup_env()
    async with aiohttp.ClientSession(timeout=1) as session:
        yield session
