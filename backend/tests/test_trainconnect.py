"""Backend regression tests for TrainConnect Europe API."""
import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://analyze-improve-6.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# -------- Fixtures --------
@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def test_user(client):
    """Create or login demo user."""
    email = "demo@trainconnect.eu"
    pw = "demo123"
    r = client.post(f"{API}/auth/register", json={"email": email, "password": pw, "name": "Demo"}, timeout=15)
    if r.status_code == 409:
        r = client.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code in (200, 201), f"auth failed: {r.status_code} {r.text}"
    data = r.json()
    return {"token": data["token"], "user": data["user"], "email": email, "password": pw}


@pytest.fixture(scope="session")
def auth_headers(test_user):
    return {"Authorization": f"Bearer {test_user['token']}", "Content-Type": "application/json"}


# -------- Health --------
def test_root(client):
    r = client.get(f"{API}/", timeout=10)
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "ok"
    assert "name" in j


# -------- Popular routes --------
def test_popular_routes(client):
    r = client.get(f"{API}/popular-routes", timeout=10)
    assert r.status_code == 200
    routes = r.json()
    assert isinstance(routes, list)
    assert len(routes) >= 8
    sample = routes[0]
    assert sample.get("from") and sample.get("to")
    assert sample["from"].get("name") and sample["to"].get("name")


# -------- Stations --------
def test_stations_all(client):
    r = client.get(f"{API}/stations", timeout=10)
    assert r.status_code == 200
    stations = r.json()
    assert isinstance(stations, list)
    assert len(stations) >= 53


def test_stations_search_berlin(client):
    r = client.get(f"{API}/stations/search", params={"q": "berlin"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    names = " ".join(s.get("name", "") for s in data).lower()
    assert "berlin" in names


def test_station_departures_stavanger(client):
    r = client.get(f"{API}/stations/7610155/departures", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["station"]["id"] == "7610155"
    assert data["station"]["name"] == "Stavanger"
    assert isinstance(data["departures"], list)
    assert len(data["departures"]) > 0
    assert data.get("data_source") in ("live", "curated")


# -------- Auth --------
def test_register_and_login(client):
    email = f"test_{uuid.uuid4().hex[:8]}@trainconnect.eu"
    r = client.post(f"{API}/auth/register", json={"email": email, "password": "Pass1234", "name": "T"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "token" in data and len(data["token"]) > 10
    assert data["user"]["email"] == email
    # login
    r2 = client.post(f"{API}/auth/login", json={"email": email, "password": "Pass1234"}, timeout=15)
    assert r2.status_code == 200
    assert "token" in r2.json()


def test_auth_me(client, auth_headers, test_user):
    r = client.get(f"{API}/auth/me", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == test_user["email"]
    assert "id" in me
    assert "password" not in me


def test_auth_me_unauthorized(client):
    r = client.get(f"{API}/auth/me", timeout=10)
    assert r.status_code == 401


# -------- Journeys --------
@pytest.fixture(scope="session")
def journey_search_result(client):
    # Stavanger -> Athína
    r = client.post(
        f"{API}/journeys/search",
        json={"from_id": "7610155", "to_id": "5400600", "passengers": 1},
        timeout=30,
    )
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    return r.json()


def test_journeys_search_returns_4_results(journey_search_result):
    assert len(journey_search_result["results"]) == 4


def test_journeys_search_multileg_corridor(journey_search_result):
    first = journey_search_result["results"][0]
    # Stavanger -> Athína via trunk route: should be >=8 legs
    assert len(first["legs"]) >= 8, f"Expected >=8 legs, got {len(first['legs'])}"
    # legs chained
    for i in range(len(first["legs"]) - 1):
        assert first["legs"][i]["to"]["id"] == first["legs"][i + 1]["from"]["id"]


def test_journey_detail(client, journey_search_result):
    jid = journey_search_result["results"][0]["id"]
    r = client.get(f"{API}/journeys/{jid}", timeout=10)
    assert r.status_code == 200
    j = r.json()
    assert j["id"] == jid
    assert len(j["legs"]) >= 8


def test_journey_live(client, journey_search_result):
    jid = journey_search_result["results"][0]["id"]
    r = client.get(f"{API}/journeys/{jid}/live", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["journey_id"] == jid
    assert isinstance(data["legs"], list)
    assert len(data["legs"]) >= 8
    for leg in data["legs"]:
        assert leg["status"] in ("scheduled", "in_transit", "arrived")
        assert isinstance(leg["current_position"], list) and len(leg["current_position"]) == 2


# -------- Cart --------
@pytest.fixture(scope="session")
def cart(client, journey_search_result, auth_headers):
    jid = journey_search_result["results"][0]["id"]
    r = client.post(
        f"{API}/cart",
        json=[{"journey_id": jid, "passengers": 1}],
        headers=auth_headers,
        timeout=15,
    )
    assert r.status_code == 200, f"cart create failed: {r.status_code} {r.text}"
    return r.json()


def test_cart_created(cart):
    assert cart["total"] > 0
    assert len(cart["items"]) == 1
    assert "id" in cart


def test_cart_fetch(client, cart):
    r = client.get(f"{API}/cart/{cart['id']}", timeout=10)
    assert r.status_code == 200
    assert r.json()["id"] == cart["id"]


# -------- Checkout --------
@pytest.fixture(scope="session")
def checkout_session(client, cart, auth_headers):
    r = client.post(
        f"{API}/checkout/session",
        json={"origin_url": BASE_URL, "cart_id": cart["id"]},
        headers=auth_headers,
        timeout=30,
    )
    assert r.status_code == 200, f"checkout failed: {r.status_code} {r.text}"
    return r.json()


def test_checkout_session_url(checkout_session):
    assert "url" in checkout_session
    assert "session_id" in checkout_session
    assert "checkout.stripe.com" in checkout_session["url"]


def test_checkout_status(client, checkout_session):
    sid = checkout_session["session_id"]
    r = client.get(f"{API}/payments/v1/checkout/status/{sid}", timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert data["payment_status"] in ("unpaid", "paid", "no_payment_required")
    assert data["status"] in ("open", "complete", "expired")


# -------- Tickets --------
def test_tickets_list_empty(client, auth_headers):
    r = client.get(f"{API}/tickets", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    # tickets only materialize after paid; for new user should be empty
    # (demo user may have prior tickets; just assert list)


# -------- PWA --------
def test_manifest_reachable():
    r = requests.get(f"{BASE_URL}/manifest.json", timeout=10)
    assert r.status_code == 200
    m = r.json()
    assert "name" in m or "short_name" in m


def test_sw_reachable():
    r = requests.get(f"{BASE_URL}/sw.js", timeout=10)
    assert r.status_code == 200
    assert "javascript" in r.headers.get("content-type", "").lower() or len(r.text) > 50
