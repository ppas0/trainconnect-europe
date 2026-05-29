"""Phase 4 backend tests: stations DB (~51k), iCal, Apple Wallet (.pkpass), and funnel."""
import io
import os
import time
import uuid
import zipfile
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

# ---------- helpers ----------

@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers["Content-Type"] = "application/json"
    return s


@pytest.fixture(scope="module")
def user_token(client):
    ts = int(time.time())
    email = f"waltest+{ts}@trainconnect.eu"
    pwd = "walletpass1"
    client.post(f"{API}/auth/register", json={"email": email, "password": pwd, "name": "Wal Test"})
    r = client.post(f"{API}/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200, r.text
    body = r.json()
    return {"token": body["token"], "user_id": body["user"]["id"]}


@pytest.fixture(scope="module")
def auth_client(client, user_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {user_token['token']}"})
    return s


@pytest.fixture(scope="module")
def mongo_db():
    url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    name = os.environ.get("DB_NAME", "trainconnect_db")
    client = AsyncIOMotorClient(url)
    return client[name]


# ---------- stations DB ----------

class TestStationsDB:
    def test_count(self, client):
        r = client.get(f"{API}/stations/count")
        assert r.status_code == 200
        d = r.json()
        assert d["seed"] == 114
        assert d["eu_stations"] >= 50000, d
        assert d["total"] >= 51000

    def test_search_hattenheim_small_german_station(self, client):
        r = client.get(f"{API}/stations/search", params={"q": "hattenheim"})
        assert r.status_code == 200
        data = r.json()
        assert any(s["id"].startswith("tl_") and "hattenheim" in s["name"].lower() for s in data), data

    def test_search_carcassonne(self, client):
        r = client.get(f"{API}/stations/search", params={"q": "carcassonne"})
        assert r.status_code == 200
        data = r.json()
        assert any(s["country"] == "FR" and "carcassonne" in s["name"].lower() for s in data)

    def test_search_berlin_seed_precedence(self, client):
        r = client.get(f"{API}/stations/search", params={"q": "berlin"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) > 0
        # Seed Berlin Hauptbahnhof (id 8011160) must be first
        assert data[0]["id"] == "8011160", data[0]


# ---------- journeys & funnel ----------

class TestJourneySearchAndFunnel:
    def test_seed_to_seed_journey_stavanger_athina(self, client):
        r = client.post(f"{API}/journeys/search", json={"from_id": "7610155", "to_id": "5400600", "passengers": 1})
        assert r.status_code == 200, r.text
        d = r.json()
        assert "results" in d
        assert len(d["results"]) >= 1
        # multi-leg
        assert any(len(j["legs"]) > 1 for j in d["results"])

    def test_seed_to_trainline_journey(self, client):
        # Berlin Hbf (seed) -> Carcassonne (tl_1119)
        r = client.post(f"{API}/journeys/search", json={"from_id": "8011160", "to_id": "tl_1119", "passengers": 1})
        # Should not 404 due to unknown station
        assert r.status_code == 200, r.text
        d = r.json()
        assert "results" in d

    def test_funnel_searches_increments(self, client, auth_client):
        # Read before
        s0 = auth_client.get(f"{API}/affiliate/stats").json()["funnel"]["searches"]
        client.post(f"{API}/journeys/search", json={"from_id": "7610155", "to_id": "5400600", "passengers": 1})
        time.sleep(0.5)
        s1 = auth_client.get(f"{API}/affiliate/stats").json()["funnel"]["searches"]
        assert s1 >= s0 + 1

    def test_cart_events_increment(self, client, auth_client):
        # do a search to get a journey
        r = client.post(f"{API}/journeys/search", json={"from_id": "7610155", "to_id": "5400600", "passengers": 1})
        jid = r.json()["results"][0]["id"]
        c0 = auth_client.get(f"{API}/affiliate/stats").json()["funnel"]["cart_adds"]
        rc = auth_client.post(f"{API}/cart", json=[{"journey_id": jid, "passengers": 1}])
        assert rc.status_code == 200, rc.text
        time.sleep(0.5)
        c1 = auth_client.get(f"{API}/affiliate/stats").json()["funnel"]["cart_adds"]
        assert c1 >= c0 + 1


# ---------- affiliate stats funnel shape ----------

class TestAffiliateStatsFunnel:
    def test_stats_shape(self, auth_client):
        r = auth_client.get(f"{API}/affiliate/stats")
        assert r.status_code == 200
        d = r.json()
        # funnel block
        f = d["funnel"]
        for k in ("searches", "cart_adds", "outbound_clicks", "paid_checkouts",
                  "search_to_click_rate", "click_to_paid_rate"):
            assert k in f, f"missing funnel.{k}"
        # extras
        for k in ("top_searches", "missed_routes", "by_provider", "by_country", "top_routes", "recent"):
            assert k in d, f"missing {k}"
        assert isinstance(d["top_searches"], list)
        assert isinstance(d["missed_routes"], list)


# ---------- ticket exports (ics/pkpass/pdf) ----------

@pytest.fixture(scope="module")
def seed_ticket(mongo_db, user_token):
    """Insert a deterministic test ticket directly into db.tickets (and a matching journey_cache)."""
    loop = asyncio.new_event_loop()
    try:
        async def _setup():
            uid = user_token["user_id"]

            jid = f"TESTJ-{uuid.uuid4().hex[:8]}"
            tid = f"TESTT-{uuid.uuid4().hex[:8]}"
            pnr = f"TC{uuid.uuid4().hex[:6].upper()}"
            journey = {
                "_id": jid,
                "legs": [
                    {
                        "from": {"name": "Berlin Hauptbahnhof", "city": "Berlin", "lat": 52.5251, "lon": 13.3694},
                        "to": {"name": "München Hbf", "city": "München", "lat": 48.1402, "lon": 11.5582},
                        "departure": "2026-03-15T08:00:00+01:00",
                        "arrival": "2026-03-15T12:00:00+01:00",
                        "operator": "DB",
                        "train_no": "ICE 599",
                        "platform": "7",
                    },
                ],
            }
            ticket = {
                "_id": tid,
                "user_id": uid,
                "journey_id": jid,
                "pnr": pnr,
                "from": "Berlin",
                "to": "München",
                "departure": "2026-03-15T08:00:00+01:00",
                "passengers": 1,
                "price": 89.90,
                "status": "paid",
            }
            await mongo_db.journey_cache.insert_one(journey)
            await mongo_db.tickets.insert_one(ticket)
            return tid, pnr
        return loop.run_until_complete(_setup())
    finally:
        loop.close()


class TestTicketExports:
    def test_pdf_with_query_token(self, seed_ticket, user_token):
        tid, _ = seed_ticket
        r = requests.get(f"{API}/tickets/{tid}/pdf", params={"token": user_token["token"]})
        assert r.status_code == 200, r.text
        # PDF magic bytes
        assert r.content[:4] == b"%PDF", r.content[:20]

    def test_ics_with_query_token(self, seed_ticket, user_token):
        tid, pnr = seed_ticket
        r = requests.get(f"{API}/tickets/{tid}/ics", params={"token": user_token["token"]})
        assert r.status_code == 200, r.text
        assert "text/calendar" in r.headers.get("content-type", "")
        body = r.text
        assert "BEGIN:VCALENDAR" in body
        assert "END:VCALENDAR" in body
        assert "BEGIN:VEVENT" in body
        assert "BEGIN:VALARM" in body
        assert "TRIGGER:-PT30M" in body
        assert pnr in body

    def test_ics_requires_token(self, seed_ticket):
        tid, _ = seed_ticket
        r = requests.get(f"{API}/tickets/{tid}/ics")
        assert r.status_code in (401, 403)

    def test_pkpass_with_query_token(self, seed_ticket, user_token):
        tid, pnr = seed_ticket
        r = requests.get(f"{API}/tickets/{tid}/pkpass", params={"token": user_token["token"]})
        assert r.status_code == 200, r.text
        assert "application/vnd.apple.pkpass" in r.headers.get("content-type", "")
        # validate ZIP
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = set(zf.namelist())
        for f in ("pass.json", "icon.png", "icon@2x.png", "manifest.json", "signature"):
            assert f in names, f"pkpass missing {f}: {names}"
        import json as _j
        pj = _j.loads(zf.read("pass.json"))
        assert pj["serialNumber"] == pnr
        assert pj["boardingPass"]["transitType"] == "PKTransitTypeTrain"
        manifest = _j.loads(zf.read("manifest.json"))
        assert "pass.json" in manifest
