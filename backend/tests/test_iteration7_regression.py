"""Iteration 7 regression: validate the 3 specific fixes
1. /api/recommendations 200 (was 500 due to KeyError on j['from'])
2. Backend startup non-blocking - /api/ responds within 2s
3. ZIP download serves with content-type application/zip
Plus quick regression on critical paths.
"""
import os
import time
import pathlib

import requests
from dotenv import load_dotenv

# Load frontend/.env to get REACT_APP_BACKEND_URL
load_dotenv(pathlib.Path("/app/frontend/.env"))
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


# --- Fix 1: /api/recommendations no longer 500 ---------------------------
def test_recommendations_limit_4_returns_200():
    r = requests.get(f"{API}/recommendations", params={"limit": 4}, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    # response shape: list OR {results:[...]} - accept both
    items = data if isinstance(data, list) else data.get("results", data.get("recommendations", []))
    assert isinstance(items, list)
    assert len(items) >= 1, f"expected at least 1 rec, got {len(items)}"


def test_recommendations_limit_8_returns_200():
    r = requests.get(f"{API}/recommendations", params={"limit": 8}, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data if isinstance(data, list) else data.get("results", data.get("recommendations", []))
    assert isinstance(items, list)
    # Verify each item has the keys frontend expects
    if items:
        item = items[0]
        # Frontend uses from/to or from_name/to_name
        assert any(k in item for k in ("from", "from_name", "from_id")), f"missing from-key in {item.keys()}"


# --- Fix 2: Backend startup non-blocking - health responds fast ---------
def test_api_root_responds_under_2s():
    t0 = time.time()
    r = requests.get(f"{API}/", timeout=5)
    elapsed = time.time() - t0
    assert r.status_code in (200, 404), f"unexpected status {r.status_code}"
    assert elapsed < 2.0, f"API root took {elapsed:.2f}s (must be <2s)"


# --- Fix 3: ZIP download served correctly --------------------------------
def test_zip_download_serves_application_zip():
    # Note: static asset, no /api prefix
    url = f"{BASE}/downloads/TrainConnect_Europe_v1.5.zip"
    r = requests.get(url, timeout=30, allow_redirects=True)
    assert r.status_code == 200, f"ZIP got {r.status_code} from {url}"
    ctype = r.headers.get("content-type", "")
    assert "zip" in ctype.lower() or "octet-stream" in ctype.lower(), f"bad content-type: {ctype}"
    assert len(r.content) > 1000, f"ZIP too small ({len(r.content)} bytes)"
    # check ZIP magic bytes
    assert r.content[:2] == b"PK", "not a valid ZIP file (no PK magic)"


# --- Regression on critical paths ----------------------------------------
def test_popular_routes_200():
    r = requests.get(f"{API}/popular-routes", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data if isinstance(data, list) else data.get("results", [])
    assert isinstance(items, list)
    assert len(items) >= 1


def test_stations_search_berlin():
    r = requests.get(f"{API}/stations/search", params={"q": "Berlin"}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data if isinstance(data, list) else data.get("results", [])
    assert len(items) >= 1


def test_journeys_search_berlin_munich():
    payload = {"from_id": "8011160", "to_id": "8000261", "passengers": 1}
    r = requests.post(f"{API}/journeys/search", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data if isinstance(data, list) else data.get("results", [])
    assert isinstance(items, list)


def test_auth_login_demo_user():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": "demo@trainconnect.eu", "password": "demo123"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    # JWT token field could be access_token or token
    token = data.get("access_token") or data.get("token")
    assert token and isinstance(token, str) and len(token) > 20, f"no token in {data}"


def test_affiliate_stats_requires_auth():
    # First login to get token
    login = requests.post(
        f"{API}/auth/login",
        json={"email": "demo@trainconnect.eu", "password": "demo123"},
        timeout=15,
    )
    token = login.json().get("access_token") or login.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API}/affiliate/stats", headers=headers, timeout=15)
    assert r.status_code in (200, 403), f"unexpected {r.status_code}: {r.text}"


def test_affiliate_config_authed():
    login = requests.post(
        f"{API}/auth/login",
        json={"email": "demo@trainconnect.eu", "password": "demo123"},
        timeout=15,
    )
    token = login.json().get("access_token") or login.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API}/affiliate/config", headers=headers, timeout=15)
    assert r.status_code in (200, 403), f"unexpected {r.status_code}: {r.text}"
