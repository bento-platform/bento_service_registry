import os
import pytest
import pytest_asyncio


def _setup_env():
    os.environ["CHORD_SERVICES"] = os.path.join(os.path.dirname(__file__), "chord_services.json")
    os.environ["URL_PATH_FORMAT"] = ""  # Mount off of root URL for testing
    os.environ["CHORD_DEBUG"] = ""


@pytest.fixture()
def client():
    _setup_env()
    from bento_service_registry.app import application
    yield application.test_client()


async def _service_info_fixt():
    from bento_service_registry.app import application, get_service_info
    async with application.app_context():
        return await get_service_info()


@pytest_asyncio.fixture()
async def service_info():
    _setup_env()
    yield _service_info_fixt()
