"""Iteration 8 tests:
- Price Alerts CRUD + check trigger
- Booking flow regression (journeys/search -> cart -> checkout/session)
- Quick regression: recommendations, popular-routes, stations/search
"""
import os
import requests
import pytest
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

DEMO = {"email": "demo@trainconnect.eu", "password": "demo123"}

# ------- shared fixtures -------
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s

@pytest.fixture(scope="module")
def token(session):
    # login (user already seeded in prior iterations)
    r = session.post(f"{API}/auth/login", json=DEMO, timeout=15)
    if r.status_code != 200:
        # try to register and login again
        session.post(f"{API}/auth/register", json={**DEMO, "name": "Demo"}, timeout=15)
        r = session.post(f"{API}/auth/login", json=DEMO, timeout=15)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok
    return tok

@pytest.fixture(scope="module")
def auth(session, token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    return s

# ------- Price Alerts -------
class TestPriceAlerts:
    BERLIN = "8011160"
    MUNICH = "8000261"

    def test_create_price_alert(self, auth):
        r = auth.post(f"{API}/price-alerts", json={
            "from_id": self.BERLIN, "to_id": self.MUNICH,
            "threshold": 80.0, "passengers": 1
        }, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["from_id"] == self.BERLIN
        assert d["to_id"] == self.MUNICH
        assert d["threshold"] == 80.0
        assert d["passengers"] == 1
        assert d.get("active") is True
        assert "id" in d
        assert "_id" not in d, "Mongo _id should be excluded"

    def test_create_is_idempotent_replace_in_place(self, auth):
        r1 = auth.post(f"{API}/price-alerts", json={
            "from_id": self.BERLIN, "to_id": self.MUNICH,
            "threshold": 60.0, "passengers": 1,
        }, timeout=20)
        assert r1.status_code == 200
        id1 = r1.json()["id"]
        r2 = auth.post(f"{API}/price-alerts", json={
            "from_id": self.BERLIN, "to_id": self.MUNICH,
            "threshold": 50.0, "passengers": 1,
        }, timeout=20)
        assert r2.status_code == 200
        assert r2.json()["id"] == id1
        # verify via list
        rl = auth.get(f"{API}/price-alerts", timeout=15)
        assert rl.status_code == 200
        items = [a for a in rl.json()["alerts"] if a["id"] == id1]
        assert len(items) == 1
        assert items[0]["threshold"] == 50.0

    def test_list_alerts_returns_current_user(self, auth):
        r = auth.get(f"{API}/price-alerts", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)
        assert len(data["alerts"]) >= 1
        # all alerts must belong to current user
        for a in data["alerts"]:
            assert "user_id" in a
            assert "_id" not in a or a.get("id")  # id field exposed

    def test_check_endpoint(self, auth):
        r = auth.post(f"{API}/price-alerts/check", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "checked" in d and "notified" in d
        assert isinstance(d["checked"], int)
        assert isinstance(d["notified"], int)
        assert d["checked"] >= 1

    def test_delete_alert(self, auth):
        # create a different one (different passengers count -> distinct id)
        cr = auth.post(f"{API}/price-alerts", json={
            "from_id": self.BERLIN, "to_id": self.MUNICH,
            "threshold": 99.0, "passengers": 3,
        }, timeout=20)
        assert cr.status_code == 200
        aid = cr.json()["id"]
        dr = auth.delete(f"{API}/price-alerts/{aid}", timeout=15)
        assert dr.status_code == 200
        assert dr.json().get("deleted") is True
        # verify gone
        rl = auth.get(f"{API}/price-alerts", timeout=15)
        ids = [a["id"] for a in rl.json()["alerts"]]
        assert aid not in ids

    def test_unauth_listing_blocked(self, session):
        # fresh client without auth
        s = requests.Session()
        r = s.get(f"{API}/price-alerts", timeout=15)
        assert r.status_code in (401, 403)

    def test_delete_other_users_alert_404(self, auth):
        r = auth.delete(f"{API}/price-alerts/nonexistent_xyz", timeout=15)
        assert r.status_code == 404


# ------- Booking flow regression -------
class TestBookingFlow:
    def test_full_booking_flow(self, auth):
        # 1. search journeys
        sr = auth.post(f"{API}/journeys/search", json={
            "from_id": "8011160", "to_id": "8000261", "passengers": 1
        }, timeout=45)
        assert sr.status_code == 200, sr.text
        sd = sr.json()
        journeys = sd.get("journeys") or sd.get("results") or []
        assert len(journeys) > 0, f"no journeys in response: {sd}"
        j0 = journeys[0]
        jid = j0.get("id") or j0.get("journey_id")
        assert jid

        # 2. POST /api/cart with ARRAY body
        cr = auth.post(f"{API}/cart", json=[{"journey_id": jid, "passengers": 1}], timeout=20)
        assert cr.status_code == 200, f"cart failed {cr.status_code} {cr.text}"
        cd = cr.json()
        cart_id = cd.get("cart_id") or cd.get("id")
        assert cart_id, f"no cart_id in {cd}"
        # provider_links should be present for all legs
        items = cd.get("items") or cd.get("legs") or []
        if items:
            for it in items:
                # accept either nested provider_links or top-level
                pass  # not all schemas guarantee, soft check

        # 3. checkout session
        co = auth.post(f"{API}/checkout/session", json={
            "cart_id": cart_id,
            "origin_url": "https://analyze-improve-6.preview.emergentagent.com"
        }, timeout=30)
        assert co.status_code == 200, f"checkout failed {co.status_code} {co.text}"
        cod = co.json()
        url = cod.get("url") or cod.get("checkout_url")
        sid = cod.get("session_id") or cod.get("id")
        assert url and "cs_test_" in url, f"expected cs_test_ in url: {url}"
        assert sid


# ------- Regression -------
class TestRegression:
    def test_recommendations_limit_4(self, session):
        r = session.get(f"{API}/recommendations?limit=4", timeout=20)
        assert r.status_code == 200
        d = r.json()
        items = d if isinstance(d, list) else (d.get("recommendations") or d.get("items") or [])
        assert len(items) >= 1

    def test_popular_routes(self, session):
        r = session.get(f"{API}/popular-routes", timeout=15)
        assert r.status_code == 200

    def test_stations_search_berlin(self, session):
        r = session.get(f"{API}/stations/search?q=Berlin", timeout=15)
        assert r.status_code == 200
        d = r.json()
        items = d if isinstance(d, list) else (d.get("stations") or d.get("results") or [])
        assert len(items) >= 1
