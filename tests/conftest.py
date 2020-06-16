import os
import pytest


def _setup_env():
    os.environ["CHORD_SERVICES"] = os.path.join(os.path.dirname(__file__), "chord_services.json")
    os.environ["URL_PATH_FORMAT"] = ""  # Mount off of root URL for testing


@pytest.fixture()
def client():
    _setup_env()
    from bento_service_registry.app import application
    yield application.test_client()


@pytest.fixture()
def service_info():
    _setup_env()
    from bento_service_registry.app import SERVICE_INFO
    yield SERVICE_INFO
