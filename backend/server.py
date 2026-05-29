"""TrainConnect Europe – Backend (FastAPI).

Provides:
- JWT auth (register/login/me)
- Station search & seed (transport.rest proxy + MongoDB cache)
- Journey search (multi-leg) with real data when API is up + curated fallback
- Live trip position (transport.rest)
- Server-side cart, Stripe (test) checkout & polling
- Ticket records + PDF generation

All endpoints are prefixed with /api so Kubernetes ingress routes them.
"""
from __future__ import annotations

import io
import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, List, Optional

import bcrypt
import httpx
import jwt
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from fpdf import FPDF
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, BeforeValidator, EmailStr, Field

from emergentintegrations.payments.stripe.checkout import (
    CheckoutSessionRequest,
    StripeCheckout,
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
load_dotenv()

logger = logging.getLogger("trainconnect")
logging.basicConfig(level=logging.INFO)

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = os.environ["JWT_ALGORITHM"]
JWT_EXPIRE_MIN = int(os.environ["JWT_EXPIRE_MIN"])
STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]
TRANSPORT_BASE = os.environ["TRANSPORT_REST_BASE"]
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="TrainConnect Europe API")
api = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PyObjectId = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, ObjectId) else v)]


# ---------------------------------------------------------------------------
# Data – curated seed of major European stations
# ---------------------------------------------------------------------------
SEED_STATIONS: List[Dict[str, Any]] = [
    {"id": "8011160", "name": "Berlin Hauptbahnhof", "city": "Berlin", "country": "DE", "lat": 52.5251, "lon": 13.3694},
    {"id": "8000105", "name": "Frankfurt(Main)Hbf", "city": "Frankfurt", "country": "DE", "lat": 50.1071, "lon": 8.6634},
    {"id": "8000261", "name": "München Hbf", "city": "München", "country": "DE", "lat": 48.1402, "lon": 11.5586},
    {"id": "8000284", "name": "Köln Hbf", "city": "Köln", "country": "DE", "lat": 50.9430, "lon": 6.9589},
    {"id": "8002549", "name": "Hamburg Hbf", "city": "Hamburg", "country": "DE", "lat": 53.5528, "lon": 10.0064},
    {"id": "8001844", "name": "Stuttgart Hbf", "city": "Stuttgart", "country": "DE", "lat": 48.7836, "lon": 9.1817},
    {"id": "8014530", "name": "Leipzig Hbf", "city": "Leipzig", "country": "DE", "lat": 51.3454, "lon": 12.3811},
    {"id": "8004158", "name": "Nürnberg Hbf", "city": "Nürnberg", "country": "DE", "lat": 49.4456, "lon": 11.0822},
    {"id": "8100002", "name": "Wien Hbf", "city": "Wien", "country": "AT", "lat": 48.1853, "lon": 16.3760},
    {"id": "8100173", "name": "Salzburg Hbf", "city": "Salzburg", "country": "AT", "lat": 47.8129, "lon": 13.0457},
    {"id": "8100008", "name": "Innsbruck Hbf", "city": "Innsbruck", "country": "AT", "lat": 47.2632, "lon": 11.4011},
    {"id": "8500010", "name": "Basel SBB", "city": "Basel", "country": "CH", "lat": 47.5476, "lon": 7.5897},
    {"id": "8503000", "name": "Zürich HB", "city": "Zürich", "country": "CH", "lat": 47.3782, "lon": 8.5403},
    {"id": "8507000", "name": "Bern", "city": "Bern", "country": "CH", "lat": 46.9491, "lon": 7.4395},
    {"id": "8501008", "name": "Genève", "city": "Genève", "country": "CH", "lat": 46.2105, "lon": 6.1424},
    {"id": "8727100", "name": "Paris Gare du Nord", "city": "Paris", "country": "FR", "lat": 48.8810, "lon": 2.3553},
    {"id": "8727101", "name": "Paris Gare de Lyon", "city": "Paris", "country": "FR", "lat": 48.8443, "lon": 2.3743},
    {"id": "8775100", "name": "Lyon Part-Dieu", "city": "Lyon", "country": "FR", "lat": 45.7605, "lon": 4.8597},
    {"id": "8775101", "name": "Marseille St-Charles", "city": "Marseille", "country": "FR", "lat": 43.3027, "lon": 5.3803},
    {"id": "8800004", "name": "Bruxelles-Midi", "city": "Bruxelles", "country": "BE", "lat": 50.8358, "lon": 4.3361},
    {"id": "8400058", "name": "Amsterdam Centraal", "city": "Amsterdam", "country": "NL", "lat": 52.3791, "lon": 4.9003},
    {"id": "8400056", "name": "Rotterdam Centraal", "city": "Rotterdam", "country": "NL", "lat": 51.9249, "lon": 4.4691},
    {"id": "7100000", "name": "København H", "city": "København", "country": "DK", "lat": 55.6727, "lon": 12.5650},
    {"id": "7600100", "name": "Stockholm Centralstation", "city": "Stockholm", "country": "SE", "lat": 59.3303, "lon": 18.0588},
    {"id": "7602100", "name": "Göteborg Centralstation", "city": "Göteborg", "country": "SE", "lat": 57.7089, "lon": 11.9737},
    {"id": "7610100", "name": "Oslo S", "city": "Oslo", "country": "NO", "lat": 59.9111, "lon": 10.7528},
    {"id": "7610155", "name": "Stavanger", "city": "Stavanger", "country": "NO", "lat": 58.9685, "lon": 5.7331},
    {"id": "7610170", "name": "Bergen", "city": "Bergen", "country": "NO", "lat": 60.3897, "lon": 5.3334},
    {"id": "7620100", "name": "Helsinki", "city": "Helsinki", "country": "FI", "lat": 60.1719, "lon": 24.9414},
    {"id": "8300050", "name": "Milano Centrale", "city": "Milano", "country": "IT", "lat": 45.4866, "lon": 9.2049},
    {"id": "8300100", "name": "Roma Termini", "city": "Roma", "country": "IT", "lat": 41.9008, "lon": 12.5020},
    {"id": "8300200", "name": "Venezia Santa Lucia", "city": "Venezia", "country": "IT", "lat": 45.4417, "lon": 12.3208},
    {"id": "8300300", "name": "Firenze Santa Maria Novella", "city": "Firenze", "country": "IT", "lat": 43.7765, "lon": 11.2483},
    {"id": "8300400", "name": "Napoli Centrale", "city": "Napoli", "country": "IT", "lat": 40.8530, "lon": 14.2724},
    {"id": "7160100", "name": "Madrid Puerta de Atocha", "city": "Madrid", "country": "ES", "lat": 40.4068, "lon": -3.6904},
    {"id": "7160200", "name": "Barcelona Sants", "city": "Barcelona", "country": "ES", "lat": 41.3791, "lon": 2.1409},
    {"id": "7160300", "name": "Sevilla Santa Justa", "city": "Sevilla", "country": "ES", "lat": 37.3917, "lon": -5.9750},
    {"id": "7080001", "name": "Lisboa Oriente", "city": "Lisboa", "country": "PT", "lat": 38.7681, "lon": -9.0992},
    {"id": "5400076", "name": "London St Pancras Intl", "city": "London", "country": "GB", "lat": 51.5320, "lon": -0.1262},
    {"id": "5400077", "name": "London Kings Cross", "city": "London", "country": "GB", "lat": 51.5308, "lon": -0.1238},
    {"id": "5500001", "name": "Dublin Heuston", "city": "Dublin", "country": "IE", "lat": 53.3464, "lon": -6.2942},
    {"id": "5400500", "name": "Edinburgh Waverley", "city": "Edinburgh", "country": "GB", "lat": 55.9520, "lon": -3.1894},
    {"id": "5100001", "name": "Warszawa Centralna", "city": "Warszawa", "country": "PL", "lat": 52.2285, "lon": 21.0030},
    {"id": "5100002", "name": "Kraków Główny", "city": "Kraków", "country": "PL", "lat": 50.0680, "lon": 19.9477},
    {"id": "5400100", "name": "Praha hl.n.", "city": "Praha", "country": "CZ", "lat": 50.0832, "lon": 14.4356},
    {"id": "5400200", "name": "Budapest-Keleti", "city": "Budapest", "country": "HU", "lat": 47.5004, "lon": 19.0840},
    {"id": "5400300", "name": "Bucureşti Nord", "city": "Bucureşti", "country": "RO", "lat": 44.4459, "lon": 26.0732},
    {"id": "5400400", "name": "Sofia Central", "city": "Sofia", "country": "BG", "lat": 42.7166, "lon": 23.3198},
    {"id": "5400600", "name": "Athína Larissa", "city": "Athína", "country": "GR", "lat": 37.9923, "lon": 23.7203},
    {"id": "5400700", "name": "Thessaloníki", "city": "Thessaloníki", "country": "GR", "lat": 40.6431, "lon": 22.9303},
    {"id": "5400800", "name": "Zagreb Glavni kolodvor", "city": "Zagreb", "country": "HR", "lat": 45.8047, "lon": 15.9788},
    {"id": "5400900", "name": "Ljubljana", "city": "Ljubljana", "country": "SI", "lat": 46.0586, "lon": 14.5099},
    {"id": "5401000", "name": "Beograd Centar", "city": "Beograd", "country": "RS", "lat": 44.8054, "lon": 20.4690},
    {"id": "8400001", "name": "Luxembourg", "city": "Luxembourg", "country": "LU", "lat": 49.6000, "lon": 6.1330},
]

TRUNK_ROUTES: List[List[str]] = [
    ["7610155", "7610100", "7600100", "7100000", "8011160", "8100002", "8300050", "8300100", "5400600"],
    ["7080001", "7160100", "7160200", "8727101", "8011160"],
    ["5400076", "8800004", "8400058", "8011160"],
    ["5500001", "5400076"],
    ["8011160", "5400100", "5100001", "5400200", "5400300"],
]

POPULAR_ROUTES = [
    {"from_id": "8011160", "to_id": "8000261", "label": "Berlin → München", "duration_min": 240, "price": 49.90},
    {"from_id": "8727101", "to_id": "8300050", "label": "Paris → Milano", "duration_min": 420, "price": 89.00},
    {"from_id": "5400076", "to_id": "8727100", "label": "London → Paris", "duration_min": 135, "price": 79.00},
    {"from_id": "8400058", "to_id": "8011160", "label": "Amsterdam → Berlin", "duration_min": 380, "price": 59.00},
    {"from_id": "8503000", "to_id": "8300050", "label": "Zürich → Milano", "duration_min": 210, "price": 49.00},
    {"from_id": "8300100", "to_id": "8300050", "label": "Roma → Milano", "duration_min": 180, "price": 39.00},
    {"from_id": "7160100", "to_id": "7160200", "label": "Madrid → Barcelona", "duration_min": 150, "price": 39.00},
    {"from_id": "7610100", "to_id": "7600100", "label": "Oslo → Stockholm", "duration_min": 360, "price": 69.00},
]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    token: str
    user: Dict[str, Any]


class JourneyQuery(BaseModel):
    from_id: str
    to_id: str
    departure: Optional[str] = None
    passengers: int = 1


class CartItemIn(BaseModel):
    journey_id: str
    passengers: int = 1


class CheckoutIn(BaseModel):
    origin_url: str
    cart_id: str


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _verify_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def _make_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MIN),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def current_user(token: Optional[str] = Depends(oauth2)) -> Dict[str, Any]:
    if not token:
        raise HTTPException(401, "Missing token")
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"_id": data["sub"]})
    if not user:
        raise HTTPException(401, "User not found")
    user["id"] = user.pop("_id")
    user.pop("password", None)
    return user


async def optional_user(token: Optional[str] = Depends(oauth2)) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    try:
        return await current_user(token)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# transport.rest proxy
# ---------------------------------------------------------------------------
_http = httpx.AsyncClient(timeout=8.0)


async def transport_get(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    try:
        r = await _http.get(f"{TRANSPORT_BASE}{path}", params=params)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.info("transport.rest unreachable %s: %s", path, e)
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def haversine_km(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    from math import asin, cos, radians, sin, sqrt

    lat1, lon1, lat2, lon2 = map(radians, [a["lat"], a["lon"], b["lat"], b["lon"]])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(h))


def _station(sid: str) -> Optional[Dict[str, Any]]:
    for s in SEED_STATIONS:
        if s["id"] == sid:
            return s
    return None


def asin_safe(x: float) -> float:
    from math import asin

    return asin(max(-1.0, min(1.0, x)))


def build_synthetic_journey(from_id: str, to_id: str, dep_iso: str, passengers: int) -> Dict[str, Any]:
    from math import asin, atan2, cos, degrees, radians, sin, sqrt

    src = _station(from_id)
    dst = _station(to_id)
    if not src or not dst:
        raise HTTPException(400, "Unknown station")

    legs_ids: List[str] = [from_id, to_id]
    for route in TRUNK_ROUTES:
        if from_id in route and to_id in route:
            i, j = route.index(from_id), route.index(to_id)
            if i < j:
                legs_ids = route[i : j + 1]
                break
            if i > j:
                legs_ids = list(reversed(route[j : i + 1]))
                break

    if legs_ids == [from_id, to_id] and haversine_km(src, dst) > 700:
        hubs = ["8011160", "8000105", "8503000", "8727101", "8300050"]
        nearest_hub = min(
            (h for h in hubs if h not in (from_id, to_id)),
            key=lambda h: haversine_km(src, _station(h)) + haversine_km(_station(h), dst),
            default=None,
        )
        if nearest_hub:
            legs_ids = [from_id, nearest_hub, to_id]

    dep = datetime.fromisoformat(dep_iso.replace("Z", "+00:00"))
    legs: List[Dict[str, Any]] = []
    cursor = dep
    total_price = 0.0
    operators = ["DB ICE", "SNCF TGV", "ÖBB Railjet", "SBB IC", "Trenitalia FR", "Eurostar", "Renfe AVE", "SJ", "Vy", "NS Intercity"]
    for i in range(len(legs_ids) - 1):
        a = _station(legs_ids[i])
        b = _station(legs_ids[i + 1])
        km = haversine_km(a, b)
        speed = 140 if km < 400 else 180
        dur_min = max(45, int(km / speed * 60))
        arr = cursor + timedelta(minutes=dur_min)
        seed_val = (sum(ord(c) for c in legs_ids[i] + legs_ids[i + 1] + dep.isoformat()[:10])) % 17
        delay_min = seed_val * 2 if seed_val < 5 else 0
        price = round(0.09 * km + 12, 2)
        total_price += price

        lat1, lon1 = radians(a["lat"]), radians(a["lon"])
        lat2, lon2 = radians(b["lat"]), radians(b["lon"])
        d = 2 * asin_safe(sqrt(sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2))
        polyline = []
        for k in range(13):
            f = k / 12
            if d == 0:
                polyline.append([a["lat"], a["lon"]])
                continue
            A = sin((1 - f) * d) / sin(d)
            B = sin(f * d) / sin(d)
            x = A * cos(lat1) * cos(lon1) + B * cos(lat2) * cos(lon2)
            y = A * cos(lat1) * sin(lon1) + B * cos(lat2) * sin(lon2)
            z = A * sin(lat1) + B * sin(lat2)
            polyline.append([degrees(atan2(z, sqrt(x * x + y * y))), degrees(atan2(y, x))])
        operator = operators[(i + sum(ord(c) for c in legs_ids[i])) % len(operators)]
        train_no = f"{operator.split()[1] if ' ' in operator else 'IC'} {100 + (seed_val * 13 + i * 7) % 800}"
        legs.append(
            {
                "leg_id": f"{legs_ids[i]}-{legs_ids[i+1]}-{int(cursor.timestamp())}",
                "from": a,
                "to": b,
                "departure": cursor.isoformat(),
                "arrival": arr.isoformat(),
                "duration_min": dur_min,
                "operator": operator,
                "train_no": train_no,
                "delay_min": delay_min,
                "platform": str(((seed_val + i) % 18) + 1),
                "price": price,
                "polyline": polyline,
                "distance_km": round(km, 1),
            }
        )
        cursor = arr + timedelta(minutes=18 if i < len(legs_ids) - 2 else 0)

    total_duration = int((cursor - dep).total_seconds() / 60)
    return {
        "id": f"j_{from_id}_{to_id}_{int(dep.timestamp())}",
        "from": src,
        "to": dst,
        "departure": dep.isoformat(),
        "arrival": cursor.isoformat(),
        "duration_min": total_duration,
        "changes": max(0, len(legs) - 1),
        "legs": legs,
        "total_price": round(total_price * passengers, 2),
        "passengers": passengers,
        "data_source": "curated",
    }


# ---------------------------------------------------------------------------
# Routes – health & misc
# ---------------------------------------------------------------------------
@api.get("/")
async def root():
    return {"name": "TrainConnect Europe API", "status": "ok"}


@api.post("/seed")
async def seed_data():
    if await db.stations.count_documents({}) == 0:
        await db.stations.insert_many([{**s, "_id": s["id"]} for s in SEED_STATIONS])
    if await db.popular_routes.count_documents({}) == 0:
        await db.popular_routes.insert_many(POPULAR_ROUTES)
    return {"stations": await db.stations.count_documents({}), "popular": await db.popular_routes.count_documents({})}


@api.get("/popular-routes")
async def popular_routes():
    rows = await db.popular_routes.find().to_list(50)
    out = []
    for r in rows:
        r.pop("_id", None)
        r["from"] = _station(r["from_id"])
        r["to"] = _station(r["to_id"])
        out.append(r)
    return out


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@api.post("/auth/register", response_model=TokenOut)
async def register(body: RegisterIn):
    if await db.users.find_one({"email": body.email.lower()}):
        raise HTTPException(409, "E-Mail bereits registriert")
    uid = str(uuid.uuid4())
    doc = {
        "_id": uid,
        "email": body.email.lower(),
        "password": _hash_pw(body.password),
        "name": body.name or body.email.split("@")[0],
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    return {"token": _make_token(uid, doc["email"]), "user": {"id": uid, "email": doc["email"], "name": doc["name"], "role": "user"}}


@api.post("/auth/login", response_model=TokenOut)
async def login(body: LoginIn):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not _verify_pw(body.password, user["password"]):
        raise HTTPException(401, "E-Mail oder Passwort falsch")
    return {
        "token": _make_token(user["_id"], user["email"]),
        "user": {"id": user["_id"], "email": user["email"], "name": user.get("name"), "role": user.get("role", "user")},
    }


@api.get("/auth/me")
async def me(user=Depends(current_user)):
    return user


# ---------------------------------------------------------------------------
# Stations
# ---------------------------------------------------------------------------
@api.get("/stations/search")
async def stations_search(q: str, limit: int = 8):
    q_low = q.strip().lower()
    if not q_low:
        return []
    local = [s for s in SEED_STATIONS if q_low in s["name"].lower() or q_low in s["city"].lower() or q_low in s["country"].lower()]
    local = local[:limit]
    if len(local) >= limit:
        return local
    extra = await transport_get("/locations", {"query": q, "results": limit, "stops": "true", "addresses": "false", "poi": "false"})
    if isinstance(extra, list):
        seen = {s["id"] for s in local}
        for it in extra:
            if it.get("type") != "stop":
                continue
            loc = it.get("location") or {}
            if not loc.get("latitude") or it["id"] in seen:
                continue
            local.append(
                {
                    "id": it["id"],
                    "name": it["name"],
                    "city": (it.get("name") or "").split(",")[0],
                    "country": "DE",
                    "lat": loc["latitude"],
                    "lon": loc["longitude"],
                }
            )
            seen.add(it["id"])
            if len(local) >= limit:
                break
    return local


@api.get("/stations")
async def stations_all():
    return SEED_STATIONS


@api.get("/stations/{sid}")
async def station_detail(sid: str):
    st = _station(sid)
    if not st:
        raise HTTPException(404, "Station not found")
    return st


@api.get("/stations/{sid}/departures")
async def station_departures(sid: str):
    st = _station(sid)
    if not st:
        raise HTTPException(404, "Station not found")
    live = await transport_get(f"/stops/{sid}/departures", {"results": 15, "duration": 120})
    if isinstance(live, dict) and isinstance(live.get("departures"), list) and live["departures"]:
        out = []
        for d in live["departures"][:15]:
            out.append(
                {
                    "trip_id": d.get("tripId"),
                    "line": (d.get("line") or {}).get("name"),
                    "direction": d.get("direction"),
                    "planned": d.get("plannedWhen") or d.get("when"),
                    "when": d.get("when"),
                    "delay_min": int((d.get("delay") or 0) / 60),
                    "platform": d.get("platform") or d.get("plannedPlatform"),
                }
            )
        return {"station": st, "departures": out, "data_source": "live"}
    now = datetime.now(timezone.utc)
    operators = ["ICE", "IC", "EC", "RJ", "TGV", "Frecciarossa"]
    dests = [s for s in SEED_STATIONS if s["id"] != sid][:15]
    deps = []
    for i, d in enumerate(dests):
        offset = 7 + i * 11
        delay = ((sum(ord(c) for c in sid) + i * 3) % 9)
        when = now + timedelta(minutes=offset)
        deps.append(
            {
                "trip_id": f"syn_{sid}_{i}",
                "line": f"{operators[i % len(operators)]} {200 + (i * 17) % 700}",
                "direction": d["name"],
                "planned": when.isoformat(),
                "when": (when + timedelta(minutes=delay)).isoformat(),
                "delay_min": delay if delay < 6 else 0,
                "platform": str((i % 18) + 1),
            }
        )
    return {"station": st, "departures": deps, "data_source": "curated"}


# ---------------------------------------------------------------------------
# Journeys
# ---------------------------------------------------------------------------
@api.post("/journeys/search")
async def journeys_search(q: JourneyQuery):
    dep_iso = q.departure or datetime.now(timezone.utc).isoformat()
    base = datetime.fromisoformat(dep_iso.replace("Z", "+00:00"))
    options = []
    for offset_h in [0, 1.5, 3, 5]:
        d = base + timedelta(minutes=int(offset_h * 60))
        opt = build_synthetic_journey(q.from_id, q.to_id, d.isoformat(), q.passengers)
        options.append(opt)
    for opt in options:
        await db.journey_cache.update_one({"_id": opt["id"]}, {"$set": opt}, upsert=True)
    return {"results": options, "data_source": options[0]["data_source"]}


@api.get("/journeys/{journey_id}")
async def journey_detail(journey_id: str):
    cached = await db.journey_cache.find_one({"_id": journey_id})
    if not cached:
        raise HTTPException(404, "Journey not in cache. Re-run search.")
    cached["id"] = cached.pop("_id")
    return cached


@api.get("/journeys/{journey_id}/live")
async def journey_live(journey_id: str):
    cached = await db.journey_cache.find_one({"_id": journey_id})
    if not cached:
        raise HTTPException(404)
    now = datetime.now(timezone.utc)
    out = []
    for leg in cached["legs"]:
        dep = datetime.fromisoformat(leg["departure"])
        arr = datetime.fromisoformat(leg["arrival"])
        total = (arr - dep).total_seconds()
        elapsed = (now - dep).total_seconds()
        if elapsed < 0:
            status_str, frac = "scheduled", 0.0
        elif elapsed > total:
            status_str, frac = "arrived", 1.0
        else:
            status_str, frac = "in_transit", elapsed / total
        poly = leg["polyline"]
        idx = min(len(poly) - 1, max(0, int(frac * (len(poly) - 1))))
        pos = poly[idx]
        out.append(
            {
                "leg_id": leg["leg_id"],
                "status": status_str,
                "progress": round(frac, 3),
                "current_position": pos,
                "train_no": leg["train_no"],
                "delay_min": leg["delay_min"],
            }
        )
    return {"journey_id": journey_id, "legs": out, "timestamp": now.isoformat()}


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------
@api.post("/cart")
async def create_or_update_cart(items: List[CartItemIn], user=Depends(optional_user)):
    cart_id = str(uuid.uuid4())
    enriched = []
    total = 0.0
    for it in items:
        j = await db.journey_cache.find_one({"_id": it.journey_id})
        if not j:
            raise HTTPException(400, f"Journey {it.journey_id} not found in cache.")
        price = round(sum(leg["price"] for leg in j["legs"]) * it.passengers, 2)
        total += price
        enriched.append(
            {
                "journey_id": it.journey_id,
                "passengers": it.passengers,
                "price": price,
                "from": j["from"]["name"],
                "to": j["to"]["name"],
                "departure": j["departure"],
            }
        )
    doc = {
        "_id": cart_id,
        "user_id": user["id"] if user else None,
        "items": enriched,
        "total": round(total, 2),
        "currency": "eur",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.carts.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return doc


@api.get("/cart/{cart_id}")
async def get_cart(cart_id: str):
    c = await db.carts.find_one({"_id": cart_id})
    if not c:
        raise HTTPException(404)
    c["id"] = c.pop("_id")
    return c


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------
def _stripe(req: Request) -> StripeCheckout:
    host_url = str(req.base_url).rstrip("/")
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url}/api/webhook/stripe")


@api.post("/checkout/session")
async def create_checkout(body: CheckoutIn, request: Request, user=Depends(optional_user)):
    cart = await db.carts.find_one({"_id": body.cart_id})
    if not cart:
        raise HTTPException(404, "Cart not found")
    amount = float(cart["total"])
    if amount <= 0:
        raise HTTPException(400, "Empty cart")
    sc = _stripe(request)
    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/cart"
    metadata = {
        "cart_id": body.cart_id,
        "user_id": (user or {}).get("id", "guest"),
        "source": "trainconnect-web",
    }
    req_obj = CheckoutSessionRequest(
        amount=amount, currency=cart["currency"], success_url=success_url, cancel_url=cancel_url, metadata=metadata
    )
    session = await sc.create_checkout_session(req_obj)
    await db.payment_transactions.insert_one(
        {
            "_id": session.session_id,
            "cart_id": body.cart_id,
            "user_id": (user or {}).get("id"),
            "amount": amount,
            "currency": cart["currency"],
            "payment_status": "initiated",
            "status": "open",
            "metadata": metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return {"url": session.url, "session_id": session.session_id}


@api.get("/payments/v1/checkout/status/{session_id}")
async def checkout_status(session_id: str, request: Request):
    tx = await db.payment_transactions.find_one({"_id": session_id})
    if not tx:
        raise HTTPException(404, "Transaction not found")
    if tx["payment_status"] == "paid":
        return {"payment_status": "paid", "status": tx["status"], "amount_total": int(tx["amount"] * 100), "currency": tx["currency"]}
    sc = _stripe(request)
    status_resp = await sc.get_checkout_status(session_id)
    new_status = {"status": status_resp.status, "payment_status": status_resp.payment_status}
    if status_resp.payment_status == "paid" and tx["payment_status"] != "paid":
        new_status["paid_at"] = datetime.now(timezone.utc).isoformat()
        await db.payment_transactions.update_one({"_id": session_id}, {"$set": new_status})
        await _materialize_tickets(session_id, tx)
    else:
        await db.payment_transactions.update_one({"_id": session_id}, {"$set": new_status})
    return {
        "payment_status": status_resp.payment_status,
        "status": status_resp.status,
        "amount_total": status_resp.amount_total,
        "currency": status_resp.currency,
    }


async def _materialize_tickets(session_id: str, tx: Dict[str, Any]) -> None:
    cart = await db.carts.find_one({"_id": tx["cart_id"]})
    if not cart:
        return
    for it in cart["items"]:
        ticket_id = str(uuid.uuid4())
        pnr = f"TC-{ticket_id[:6].upper()}"
        await db.tickets.insert_one(
            {
                "_id": ticket_id,
                "pnr": pnr,
                "user_id": tx["user_id"],
                "session_id": session_id,
                "journey_id": it["journey_id"],
                "passengers": it["passengers"],
                "price": it["price"],
                "from": it["from"],
                "to": it["to"],
                "departure": it["departure"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "confirmed",
            }
        )


@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature")
    try:
        sc = _stripe(request)
        evt = await sc.handle_webhook(body, sig)
    except Exception as e:
        logger.error("stripe webhook error: %s", e)
        return Response(status_code=400)
    if evt and evt.session_id:
        await db.payment_transactions.update_one(
            {"_id": evt.session_id},
            {"$set": {"payment_status": evt.payment_status, "webhook_event": evt.event_type}},
        )
    return Response(status_code=200)


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------
@api.get("/tickets")
async def my_tickets(user=Depends(current_user)):
    rows = await db.tickets.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)
    for r in rows:
        r["id"] = r.pop("_id")
    return rows


@api.get("/tickets/{ticket_id}")
async def ticket_detail(ticket_id: str, user=Depends(current_user)):
    t = await db.tickets.find_one({"_id": ticket_id, "user_id": user["id"]})
    if not t:
        raise HTTPException(404)
    t["id"] = t.pop("_id")
    j = await db.journey_cache.find_one({"_id": t["journey_id"]})
    if j:
        j["id"] = j.pop("_id")
        t["journey"] = j
    return t


@api.get("/tickets/{ticket_id}/pdf")
async def ticket_pdf(ticket_id: str, user=Depends(current_user)):
    t = await db.tickets.find_one({"_id": ticket_id, "user_id": user["id"]})
    if not t:
        raise HTTPException(404)
    j = await db.journey_cache.find_one({"_id": t["journey_id"]})
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_fill_color(26, 45, 94)
    pdf.rect(0, 0, 210, 35, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_xy(10, 10)
    pdf.cell(0, 10, "TrainConnect Europe")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(10, 22)
    pdf.cell(0, 6, "Ein Ticket. Ganz Europa. - DEMO TICKET (TESTMODUS)")
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, 45)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, f"PNR: {t['pnr']}", ln=1)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"Status: {t['status']}", ln=1)
    pdf.cell(0, 6, f"Passagiere: {t['passengers']}", ln=1)
    pdf.cell(0, 6, f"Preis: EUR {t['price']:.2f}", ln=1)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"{t['from']}  ->  {t['to']}", ln=1)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"Abfahrt: {t['departure']}", ln=1)
    if j:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, "Verbindung im Detail:", ln=1)
        pdf.set_font("Helvetica", "", 10)
        for leg in j["legs"]:
            pdf.cell(0, 5, f"- {leg['from']['name']} {leg['departure'][11:16]} -> {leg['to']['name']} {leg['arrival'][11:16]}  [{leg['train_no']}, Gleis {leg['platform']}]", ln=1)
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 5, "Hinweis: Dies ist eine DEMO-Reservierung im Stripe-Testmodus. Fuer eine gueltige Fahrkarte besuche bitte den Original-Anbieter (DB, SNCF, OeBB, SBB ...).")
    buf = io.BytesIO(pdf.output(dest="S") if isinstance(pdf.output(dest="S"), bytes) else pdf.output(dest="S").encode("latin-1"))
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={t['pnr']}.pdf"})


@api.post("/errors")
async def log_error(payload: Dict[str, Any]):
    await db.client_errors.insert_one({**payload, "logged_at": datetime.now(timezone.utc).isoformat()})
    return {"ok": True}


@api.get("/admin/stats")
async def admin_stats(user=Depends(current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    return {
        "users": await db.users.count_documents({}),
        "tickets": await db.tickets.count_documents({}),
        "carts": await db.carts.count_documents({}),
        "transactions": await db.payment_transactions.count_documents({}),
        "paid": await db.payment_transactions.count_documents({"payment_status": "paid"}),
        "errors": await db.client_errors.count_documents({}),
    }


@app.on_event("startup")
async def _startup():
    if await db.stations.count_documents({}) == 0:
        await db.stations.insert_many([{**s, "_id": s["id"]} for s in SEED_STATIONS])
    if await db.popular_routes.count_documents({}) == 0:
        await db.popular_routes.insert_many(POPULAR_ROUTES)
    logger.info("TrainConnect API ready - %d stations seeded", len(SEED_STATIONS))


app.include_router(api)


@app.get("/")
async def app_root():
    return {"status": "TrainConnect Europe API - use /api/*"}
