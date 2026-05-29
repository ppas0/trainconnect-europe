"""Phase 3 tests for TrainConnect Europe: affiliate-click tracking + stats."""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

DEMO_EMAIL = "demo@trainconnect.eu"
DEMO_PASSWORD = "demo123"


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def demo_token(client):
    """Ensure demo user exists; return JWT token."""
    r = client.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=15)
    if r.status_code != 200:
        # Register if not exists
        rr = client.post(
            f"{API}/auth/register",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "name": "Demo"},
            timeout=15,
        )
        assert rr.status_code in (200, 201, 409), rr.text
        if rr.status_code in (200, 201):
            return rr.json()["token"]
        r = client.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


# ---------- POST /api/affiliate/click ----------
def test_affiliate_click_returns_decorated_url_and_id(client):
    """Anonymous click (no auth) is allowed and returns decorated URL + click_id."""
    payload = {
        "provider": "Deutsche Bahn",
        "country": "DE",
        "leg": "Berlin → München",
        "url": "https://www.bahn.de/x",
    }
    r = client.post(f"{API}/affiliate/click", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "redirect_url" in data
    assert "click_id" in data
    assert isinstance(data["click_id"], str)
    assert len(data["click_id"]) > 0
    url = data["redirect_url"]
    assert "utm_source=trainconnect" in url
    assert "utm_medium=referral" in url
    assert "utm_campaign=multi_leg" in url
    # original URL had no '?' -> first param uses '?'
    assert "?utm_source=trainconnect" in url


def test_affiliate_click_appends_with_ampersand_when_query_exists(client):
    """URL with existing query string should append UTM with '&' not '?'."""
    payload = {
        "provider": "SNCF Connect",
        "country": "FR",
        "leg": "Paris → Lyon",
        "url": "https://www.sncf-connect.com/search?foo=bar",
    }
    r = client.post(f"{API}/affiliate/click", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    url = r.json()["redirect_url"]
    # Original ? must be preserved, UTM must be appended with &
    assert "?foo=bar&utm_source=trainconnect" in url
    # Must NOT contain two '?' separators
    assert url.count("?") == 1


def test_affiliate_click_works_with_token(client, demo_token):
    """Authenticated click also works (optional_user path)."""
    payload = {
        "provider": "Hellenic Train",
        "country": "GR",
        "leg": "Athína → Thessaloníki",
        "url": "https://hellenictrain.gr/en",
    }
    headers = {"Authorization": f"Bearer {demo_token}"}
    r = client.post(f"{API}/affiliate/click", json=payload, headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "redirect_url" in data
    assert "utm_source=trainconnect" in data["redirect_url"]


# ---------- GET /api/affiliate/stats ----------
def test_affiliate_stats_requires_auth(client):
    r = client.get(f"{API}/affiliate/stats", timeout=15)
    assert r.status_code == 401, f"Expected 401 without token, got {r.status_code}"


def test_affiliate_stats_shape_and_aggregation(client, demo_token):
    # First, generate a few clicks for aggregation
    unique_provider = f"TEST_PROV_{uuid.uuid4().hex[:6]}"
    for i in range(3):
        client.post(
            f"{API}/affiliate/click",
            json={
                "provider": unique_provider,
                "country": "DE",
                "leg": f"TEST_Leg_{i}",
                "url": "https://example.com/test",
            },
            timeout=15,
        )

    headers = {"Authorization": f"Bearer {demo_token}"}
    r = client.get(f"{API}/affiliate/stats", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()

    # Required keys
    for key in ["total_clicks", "last_7d", "by_provider", "by_country", "top_routes", "recent"]:
        assert key in data, f"missing key: {key}"

    # Types
    assert isinstance(data["total_clicks"], int)
    assert isinstance(data["last_7d"], int)
    assert isinstance(data["by_provider"], list)
    assert isinstance(data["by_country"], list)
    assert isinstance(data["top_routes"], list)
    assert isinstance(data["recent"], list)

    # After our clicks, totals should be >= 3 and at least one provider entry
    assert data["total_clicks"] >= 3
    assert len(data["by_provider"]) >= 1

    # by_provider entries shape + descending sort
    counts = [p["clicks"] for p in data["by_provider"]]
    assert counts == sorted(counts, reverse=True), "by_provider must be sorted desc by clicks"
    assert len(data["by_provider"]) <= 10
    assert len(data["by_country"]) <= 10
    assert len(data["top_routes"]) <= 10
    assert len(data["recent"]) <= 20

    # Verify our just-created provider made it into the aggregates
    provider_names = [p["name"] for p in data["by_provider"]]
    # top 10 only, but if our provider had highest fresh count it should still be there
    # Use 'recent' as a fallback verification — at least our provider should be in recent
    recent_providers = {r["provider"] for r in data["recent"]}
    assert unique_provider in recent_providers or unique_provider in provider_names

    # last_7d cannot exceed total_clicks
    assert data["last_7d"] <= data["total_clicks"]


# ---------- Regression: ensure prior endpoints still work ----------
def test_login_still_works(client):
    r = client.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    assert "token" in r.json()


def test_journey_search_still_works(client):
    r = client.post(
        f"{API}/journeys/search",
        json={"from_id": "7610155", "to_id": "5400600", "passengers": 1},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "results" in data and len(data["results"]) >= 1
    first = data["results"][0]
    assert first["from"]["id"] == "7610155"
    assert first["to"]["id"] == "5400600"
    assert len(first["legs"]) >= 1
