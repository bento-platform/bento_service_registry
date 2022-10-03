def test_service_info(client, service_info):
    r = client.get("/service-info")
    d = r.get_json()
    # TODO: Check against service-info schema
    assert r.status_code == 200
    assert d == service_info


def test_chord_service_list(client):
    r = client.get("/chord-services")
    d = r.get_json()
    assert r.status_code == 200
    assert len(d) == 1
    # TODO: Check against some schema


def test_service_list(client, service_info):
    r = client.get("/services")
    d = r.get_json()
    assert r.status_code == 200
    assert len(d) == 1
    assert d[0] == service_info


def test_service_detail(client, service_info):
    r = client.get(f"/services/{service_info['id']}")
    d = r.get_json()
    assert r.status_code == 200
    assert d == service_info

    r = client.get("/services/does-not-exist")
    assert r.status_code == 404


def test_service_type_list(client, service_info):
    r = client.get("/services/types")
    d = r.get_json()
    assert r.status_code == 200
    assert len(d) == 1
    assert d[0] == service_info["type"]
