"""Phase 5 tests: affiliate config + Web Push endpoints + URL decoration."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://analyze-improve-6.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def token(client):
    # demo user from /app/memory/test_credentials.md
    r = client.post(f"{API}/auth/login", json={"email": "demo@trainconnect.eu", "password": "demo123"})
    if r.status_code != 200:
        # auto-register fallback
        client.post(f"{API}/auth/register", json={"email": "demo@trainconnect.eu", "password": "demo123", "name": "Demo"})
        r = client.post(f"{API}/auth/login", json={"email": "demo@trainconnect.eu", "password": "demo123"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth(client, token):
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ---------- Push: public key (no auth) ----------
class TestPushPublicKey:
    def test_public_key_no_auth(self):
        r = requests.get(f"{API}/push/public-key")
        assert r.status_code == 200
        j = r.json()
        assert "public_key" in j
        assert isinstance(j["public_key"], str) and len(j["public_key"]) > 40


# ---------- Affiliate config ----------
class TestAffiliateConfig:
    def test_get_config_lists_25_providers(self, auth):
        r = auth.get(f"{API}/affiliate/config")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 25, f"expected 25 providers, got {len(data)}"
        keys = {"provider", "name", "signup_url", "affiliate_id", "notes"}
        for row in data:
            assert keys.issubset(row.keys()), f"missing keys: {keys - row.keys()}"
        # DB ICE present
        assert any(r["provider"] == "DB ICE" for r in data)

    def test_save_and_persist_affiliate_id(self, auth):
        payload = {"provider": "DB ICE", "affiliate_id": "TEST123"}
        r = auth.post(f"{API}/affiliate/config", json=payload)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        # Verify persisted via GET
        r2 = auth.get(f"{API}/affiliate/config")
        assert r2.status_code == 200
        db_ice = next(x for x in r2.json() if x["provider"] == "DB ICE")
        assert db_ice["affiliate_id"] == "TEST123"

    def test_save_unknown_provider_400(self, auth):
        r = auth.post(f"{API}/affiliate/config", json={"provider": "NOPE_FAKE_OPERATOR", "affiliate_id": "X"})
        assert r.status_code == 400, r.text


# ---------- URL decoration via journey detail ----------
class TestProviderURLDecoration:
    def test_db_ice_url_contains_aid(self, auth):
        # ensure DB ICE id is saved
        auth.post(f"{API}/affiliate/config", json={"provider": "DB ICE", "affiliate_id": "TEST123"})
        # search a DE journey: Berlin Hbf -> Munich Hbf
        r = auth.post(f"{API}/journeys/search", json={"from_id": "8011160", "to_id": "8000261", "passengers": 1})
        assert r.status_code == 200, r.text
        body = r.json()
        journeys = body.get("results") or body.get("journeys") or []
        assert journeys, f"no journeys returned: {body}"
        jid = journeys[0]["id"]
        # GET journey detail
        d = auth.get(f"{API}/journeys/{jid}")
        assert d.status_code == 200, d.text
        plinks = d.json().get("provider_links") or []
        assert plinks, "no provider_links in response"
        db_links = [p for p in plinks if p["operator"] == "DB ICE"]
        assert db_links, f"no DB ICE provider link; got {[p['operator'] for p in plinks]}"
        url = db_links[0]["url"]
        assert "aid=TEST123" in url, f"DB ICE URL not decorated with affiliate id: {url}"


# ---------- Push subscribe / unsubscribe / test / notify-delays ----------
class TestPushFlow:
    fake_endpoint = f"https://fake.example.com/{uuid.uuid4().hex}"

    def test_subscribe_persists(self, auth):
        body = {"endpoint": self.fake_endpoint, "keys": {"p256dh": "x", "auth": "y"}}
        r = auth.post(f"{API}/push/subscribe", json=body)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True
        assert "subscription_id" in j and isinstance(j["subscription_id"], str)

    def test_push_test_returns_sent_count(self, auth):
        r = auth.post(f"{API}/push/test", json={})
        assert r.status_code == 200, r.text
        j = r.json()
        assert "sent" in j and isinstance(j["sent"], int) and j["sent"] >= 0

    def test_notify_delays(self, auth):
        r = auth.post(f"{API}/push/notify-delays", json={})
        assert r.status_code == 200, r.text
        j = r.json()
        assert "checked" in j and "notified" in j
        assert isinstance(j["checked"], int) and isinstance(j["notified"], int)

    def test_unsubscribe(self, auth):
        r = auth.post(f"{API}/push/unsubscribe", json={"endpoint": self.fake_endpoint})
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ---------- Service Worker contains push handlers ----------
class TestServiceWorker:
    def test_sw_js_served_with_push_handlers(self):
        r = requests.get(f"{BASE_URL}/sw.js")
        assert r.status_code == 200, r.text
        body = r.text
        assert "push" in body
        assert "notificationclick" in body


# ---------- Regression: critical Phase 1-4 endpoints still alive ----------
class TestRegression:
    def test_stations_search_alive(self, auth):
        r = auth.get(f"{API}/stations/search", params={"q": "berlin", "limit": 5})
        assert r.status_code == 200
        results = r.json()
        assert isinstance(results, list) and len(results) > 0

    def test_stations_count_51k(self, auth):
        r = auth.get(f"{API}/stations/count")
        if r.status_code == 200:
            data = r.json()
            total = data.get("total") or data.get("count") or 0
            assert total >= 1000, f"expected at least 1000 stations, got {total}"
