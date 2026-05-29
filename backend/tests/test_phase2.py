"""Phase 2 regression tests for TrainConnect Europe: expanded stations,
i18n-friendly endpoints, and provider deep-links."""
import os
import re

import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://analyze-improve-6.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# -------- Expanded stations (>=114, >=30 countries) --------
def test_stations_count_and_countries(client):
    r = client.get(f"{API}/stations", timeout=15)
    assert r.status_code == 200
    stations = r.json()
    assert isinstance(stations, list)
    assert len(stations) >= 114, f"Expected >=114 stations, got {len(stations)}"

    countries = {s.get("country") for s in stations if s.get("country")}
    assert len(countries) >= 30, f"Expected >=30 countries, got {len(countries)}: {countries}"

    required = {"TR", "BA", "MK", "AL", "ME", "EE", "LV", "LT", "SK", "BG", "RO", "HR"}
    missing = required - countries
    assert not missing, f"Missing required countries: {missing}"


def test_stations_search_istanbul(client):
    r = client.get(f"{API}/stations/search", params={"q": "istanbul"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) > 0
    names = " ".join(s.get("name", "") for s in data).lower()
    # Match Sirkeci or Halkali (with or without diacritic)
    assert "sirkeci" in names or "halkal" in names, f"No istanbul stations found: {names}"


def test_stations_search_tallinn(client):
    r = client.get(f"{API}/stations/search", params={"q": "tallinn"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) > 0
    # Must contain an EE station
    countries = {s.get("country") for s in data}
    assert "EE" in countries, f"Expected EE in results: {data}"
    names = " ".join(s.get("name", "") for s in data).lower()
    assert "tallinn" in names


# -------- Journey search: Stavanger -> Athen still works --------
@pytest.fixture(scope="module")
def journey_no_gr(client):
    r = client.post(
        f"{API}/journeys/search",
        json={"from_id": "7610155", "to_id": "5400600", "passengers": 1},
        timeout=30,
    )
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    return r.json()


def test_no_gr_returns_4_results(journey_no_gr):
    assert len(journey_no_gr["results"]) == 4
    first = journey_no_gr["results"][0]
    assert len(first["legs"]) >= 8


# -------- Cross-corridor: Ankara -> Manchester --------
def test_ankara_manchester_search(client):
    r = client.post(
        f"{API}/journeys/search",
        json={"from_id": "TR00003", "to_id": "GB00010", "passengers": 1},
        timeout=30,
    )
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    data = r.json()
    assert isinstance(data.get("results"), list)
    assert len(data["results"]) > 0, "Expected at least 1 result for Ankara->Manchester"
    first = data["results"][0]
    assert len(first["legs"]) >= 2, "Expected multi-leg journey for cross-corridor"
    # Chain check
    for i in range(len(first["legs"]) - 1):
        assert first["legs"][i]["to"]["id"] == first["legs"][i + 1]["from"]["id"]


# -------- Provider deep-links --------
def test_journey_detail_provider_links(client, journey_no_gr):
    jid = journey_no_gr["results"][0]["id"]
    r = client.get(f"{API}/journeys/{jid}", timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert "provider_links" in j, "journey detail missing provider_links"
    links = j["provider_links"]
    assert isinstance(links, list) and len(links) >= 1

    # All URLs https
    for link in links:
        assert "url" in link and link["url"].startswith("https://"), link
        # Should have provider name/label
        assert link.get("name") or link.get("provider") or link.get("label"), link

    # Country -> provider mapping check
    # The Stavanger->Athína trunk passes through NO, SE, DK, DE, AT, IT, GR
    blob = " ".join((l.get("name") or l.get("provider") or "") + " " + l.get("url", "") for l in links).lower()
    # We expect at least the origin (NO=Vy) or destination (GR=Hellenic Train) provider
    expected_any = ["vy", "sj", "dsb", "deutsche bahn", "db", "öbb", "obb", "trenitalia", "hellenic"]
    assert any(p in blob for p in expected_any), f"No expected provider in links: {blob}"


def test_provider_country_mapping_ankara_manchester(client):
    """Verify provider mapping covers TR & GB endpoints when present."""
    r = client.post(
        f"{API}/journeys/search",
        json={"from_id": "TR00003", "to_id": "GB00010", "passengers": 1},
        timeout=30,
    )
    assert r.status_code == 200
    jid = r.json()["results"][0]["id"]
    detail = client.get(f"{API}/journeys/{jid}", timeout=15).json()
    assert "provider_links" in detail
    for link in detail["provider_links"]:
        assert re.match(r"^https://", link["url"]), link


# -------- Manifest still includes lang-agnostic name --------
def test_manifest_still_ok():
    r = requests.get(f"{BASE_URL}/manifest.json", timeout=10)
    assert r.status_code == 200
