import pytest
from bento_service_registry.app import get_bento_debug

# Cannot import anything from bento_service_registry here; has to be within
# individual tests. Otherwise, we cannot configure the environment variables
# to our liking for each test.


def test_bento_debug_off(client):
    assert not get_bento_debug()


def test_bento_debug_on(client_debug_mode):
    assert get_bento_debug()


@pytest.mark.asyncio
async def test_service_info(client):
    r = await client.get("/service-info")
    d = await r.get_json()
    # TODO: Check against service-info schema
    assert r.status_code == 200
    assert isinstance(d, dict)
    assert d["environment"] == "prod"


@pytest.mark.asyncio
async def test_service_info_debug_mode(client_debug_mode):
    r = await client_debug_mode.get("/service-info")
    d = await r.get_json()
    # TODO: Check against service-info schema
    assert r.status_code == 200
    assert isinstance(d, dict)
    assert d["environment"] == "dev"


@pytest.mark.asyncio
async def test_chord_service_list(client):
    r = await client.get("/chord-services")
    d = await r.get_json()
    assert r.status_code == 200
    assert len(d) == 1
    # TODO: Check against some schema


@pytest.mark.asyncio
async def test_service_list(client, service_info):
    service_info = await service_info

    r = await client.get("/services")
    d = await r.get_json()

    assert r.status_code == 200
    assert len(d) == 1
    assert d[0] == service_info


@pytest.mark.asyncio
async def test_service_detail(client, service_info):
    service_info = await service_info

    r = await client.get(f"/services/{service_info['id']}")
    d = await r.get_json()

    assert r.status_code == 200
    assert d == service_info

    r = await client.get("/services/does-not-exist")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_service_type_list(client, service_info):
    service_info = await service_info

    r = await client.get("/services/types")
    d = await r.get_json()

    assert r.status_code == 200
    assert len(d) == 1
    assert d[0] == service_info["type"]
