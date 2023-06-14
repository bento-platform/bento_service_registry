import pytest

# Cannot import anything from bento_service_registry here; has to be within
# individual tests. Otherwise, we cannot configure the environment variables
# to our liking for each test.


def test_service_info(client):
    r = client.get("/service-info")
    d = r.json()
    # TODO: Check against service-info schema
    assert r.status_code == 200
    assert isinstance(d, dict)
    assert d["environment"] == "prod"


def test_service_info_debug_mode(client_debug_mode):
    r = client_debug_mode.get("/service-info")
    d = r.json()
    # TODO: Check against service-info schema
    assert r.status_code == 200
    assert isinstance(d, dict)
    assert d["environment"] == "dev"


def test_bento_service_list(client):
    r = client.get("/bento-services")
    d = r.json()
    assert r.status_code == 200
    assert len(d) == 1
    # TODO: Check against some schema


@pytest.mark.asyncio
async def test_service_list(client, service_info):
    service_info = await service_info

    r = client.get("/services")
    d = r.json()

    assert r.status_code == 200
    assert len(d) == 1
    assert d[0] == service_info


@pytest.mark.asyncio
async def test_service_detail(client, service_info):
    service_info = await service_info

    r = client.get(f"/services/{service_info['id']}")
    d = r.json()

    print(f"/services/{service_info['id']}", d)

    assert r.status_code == 200
    assert d == service_info


def test_service_detail_dne(client, service_info):
    r = client.get("/services/does-not-exist")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_service_type_list(client, service_info):
    service_info = await service_info

    r = client.get("/services/types")
    d = r.json()

    assert r.status_code == 200
    assert len(d) == 1
    assert d[0] == service_info["type"]
