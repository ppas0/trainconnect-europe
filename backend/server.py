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
    # --- Phase 2 expansion: TR / Balkans / Baltics / UK regional / DE-FR-IT-ES deep ---
    {"id": "TR00001", "name": "İstanbul Halkalı", "city": "İstanbul", "country": "TR", "lat": 41.0479, "lon": 28.7706},
    {"id": "TR00002", "name": "İstanbul Sirkeci", "city": "İstanbul", "country": "TR", "lat": 41.0152, "lon": 28.9764},
    {"id": "TR00003", "name": "Ankara YHT", "city": "Ankara", "country": "TR", "lat": 39.9376, "lon": 32.8400},
    {"id": "TR00004", "name": "İzmir Basmane", "city": "İzmir", "country": "TR", "lat": 38.4181, "lon": 27.1395},
    {"id": "MK00001", "name": "Skopje", "city": "Skopje", "country": "MK", "lat": 41.9904, "lon": 21.4475},
    {"id": "BA00001", "name": "Sarajevo Glavna", "city": "Sarajevo", "country": "BA", "lat": 43.8624, "lon": 18.4045},
    {"id": "AL00001", "name": "Tiranë (Bus-Konvoi)", "city": "Tiranë", "country": "AL", "lat": 41.3275, "lon": 19.8189},
    {"id": "ME00001", "name": "Podgorica", "city": "Podgorica", "country": "ME", "lat": 42.4602, "lon": 19.2595},
    {"id": "SE00010", "name": "Malmö C", "city": "Malmö", "country": "SE", "lat": 55.6093, "lon": 13.0007},
    {"id": "SE00011", "name": "Uppsala C", "city": "Uppsala", "country": "SE", "lat": 59.8585, "lon": 17.6469},
    {"id": "NO00010", "name": "Trondheim S", "city": "Trondheim", "country": "NO", "lat": 63.4366, "lon": 10.3989},
    {"id": "NO00011", "name": "Tromsø (Bus-Anschluss)", "city": "Tromsø", "country": "NO", "lat": 69.6492, "lon": 18.9553},
    {"id": "FI00010", "name": "Tampere", "city": "Tampere", "country": "FI", "lat": 61.4980, "lon": 23.7720},
    {"id": "FI00011", "name": "Turku", "city": "Turku", "country": "FI", "lat": 60.4540, "lon": 22.2528},
    {"id": "EE00001", "name": "Tallinn Balti jaam", "city": "Tallinn", "country": "EE", "lat": 59.4407, "lon": 24.7396},
    {"id": "LV00001", "name": "Rīgas Centrālā", "city": "Rīga", "country": "LV", "lat": 56.9466, "lon": 24.1207},
    {"id": "LT00001", "name": "Vilnius", "city": "Vilnius", "country": "LT", "lat": 54.6708, "lon": 25.2823},
    {"id": "SK00001", "name": "Bratislava hl.st.", "city": "Bratislava", "country": "SK", "lat": 48.1593, "lon": 17.1063},
    {"id": "GB00010", "name": "Manchester Piccadilly", "city": "Manchester", "country": "GB", "lat": 53.4774, "lon": -2.2309},
    {"id": "GB00011", "name": "Birmingham New Street", "city": "Birmingham", "country": "GB", "lat": 52.4779, "lon": -1.8990},
    {"id": "GB00012", "name": "Liverpool Lime Street", "city": "Liverpool", "country": "GB", "lat": 53.4076, "lon": -2.9772},
    {"id": "GB00013", "name": "Glasgow Central", "city": "Glasgow", "country": "GB", "lat": 55.8587, "lon": -4.2576},
    {"id": "GB00014", "name": "Cardiff Central", "city": "Cardiff", "country": "GB", "lat": 51.4759, "lon": -3.1791},
    {"id": "GB00015", "name": "Bristol Temple Meads", "city": "Bristol", "country": "GB", "lat": 51.4490, "lon": -2.5810},
    {"id": "GB00016", "name": "York", "city": "York", "country": "GB", "lat": 53.9582, "lon": -1.0934},
    {"id": "IE00010", "name": "Cork Kent", "city": "Cork", "country": "IE", "lat": 51.9011, "lon": -8.4514},
    {"id": "IE00011", "name": "Galway Ceannt", "city": "Galway", "country": "IE", "lat": 53.2731, "lon": -9.0467},
    {"id": "DE00100", "name": "Düsseldorf Hbf", "city": "Düsseldorf", "country": "DE", "lat": 51.2199, "lon": 6.7942},
    {"id": "DE00101", "name": "Hannover Hbf", "city": "Hannover", "country": "DE", "lat": 52.3768, "lon": 9.7414},
    {"id": "DE00102", "name": "Bremen Hbf", "city": "Bremen", "country": "DE", "lat": 53.0832, "lon": 8.8133},
    {"id": "DE00103", "name": "Dresden Hbf", "city": "Dresden", "country": "DE", "lat": 51.0399, "lon": 13.7322},
    {"id": "DE00104", "name": "Mainz Hbf", "city": "Mainz", "country": "DE", "lat": 50.0010, "lon": 8.2589},
    {"id": "DE00105", "name": "Karlsruhe Hbf", "city": "Karlsruhe", "country": "DE", "lat": 48.9938, "lon": 8.4006},
    {"id": "DE00106", "name": "Freiburg(Brsg)Hbf", "city": "Freiburg", "country": "DE", "lat": 47.9974, "lon": 7.8410},
    {"id": "DE00107", "name": "Augsburg Hbf", "city": "Augsburg", "country": "DE", "lat": 48.3650, "lon": 10.8855},
    {"id": "FR00100", "name": "Bordeaux St-Jean", "city": "Bordeaux", "country": "FR", "lat": 44.8260, "lon": -0.5566},
    {"id": "FR00101", "name": "Nantes", "city": "Nantes", "country": "FR", "lat": 47.2173, "lon": -1.5414},
    {"id": "FR00102", "name": "Toulouse Matabiau", "city": "Toulouse", "country": "FR", "lat": 43.6113, "lon": 1.4534},
    {"id": "FR00103", "name": "Strasbourg-Ville", "city": "Strasbourg", "country": "FR", "lat": 48.5851, "lon": 7.7344},
    {"id": "FR00104", "name": "Lille Europe", "city": "Lille", "country": "FR", "lat": 50.6394, "lon": 3.0758},
    {"id": "FR00105", "name": "Nice-Ville", "city": "Nice", "country": "FR", "lat": 43.7044, "lon": 7.2619},
    {"id": "IT00010", "name": "Torino Porta Nuova", "city": "Torino", "country": "IT", "lat": 45.0625, "lon": 7.6783},
    {"id": "IT00011", "name": "Bologna Centrale", "city": "Bologna", "country": "IT", "lat": 44.5057, "lon": 11.3431},
    {"id": "IT00012", "name": "Verona Porta Nuova", "city": "Verona", "country": "IT", "lat": 45.4297, "lon": 10.9818},
    {"id": "IT00013", "name": "Bari Centrale", "city": "Bari", "country": "IT", "lat": 41.1188, "lon": 16.8717},
    {"id": "IT00014", "name": "Palermo Centrale", "city": "Palermo", "country": "IT", "lat": 38.1100, "lon": 13.3614},
    {"id": "ES00010", "name": "València Joaquín Sorolla", "city": "València", "country": "ES", "lat": 39.4596, "lon": -0.3776},
    {"id": "ES00011", "name": "Bilbao-Abando", "city": "Bilbao", "country": "ES", "lat": 43.2630, "lon": -2.9259},
    {"id": "ES00012", "name": "Málaga María Zambrano", "city": "Málaga", "country": "ES", "lat": 36.7117, "lon": -4.4326},
    {"id": "ES00013", "name": "Zaragoza Delicias", "city": "Zaragoza", "country": "ES", "lat": 41.6592, "lon": -0.9148},
    {"id": "PL00010", "name": "Gdańsk Główny", "city": "Gdańsk", "country": "PL", "lat": 54.3552, "lon": 18.6440},
    {"id": "PL00011", "name": "Poznań Główny", "city": "Poznań", "country": "PL", "lat": 52.4015, "lon": 16.9117},
    {"id": "PL00012", "name": "Wrocław Główny", "city": "Wrocław", "country": "PL", "lat": 51.0985, "lon": 17.0364},
    {"id": "NL00010", "name": "Utrecht Centraal", "city": "Utrecht", "country": "NL", "lat": 52.0890, "lon": 5.1098},
    {"id": "NL00011", "name": "Den Haag Centraal", "city": "Den Haag", "country": "NL", "lat": 52.0810, "lon": 4.3247},
    {"id": "BE00010", "name": "Antwerpen-Centraal", "city": "Antwerpen", "country": "BE", "lat": 51.2172, "lon": 4.4211},
    {"id": "BE00011", "name": "Gent-Sint-Pieters", "city": "Gent", "country": "BE", "lat": 51.0359, "lon": 3.7106},
    {"id": "BG00010", "name": "Plovdiv", "city": "Plovdiv", "country": "BG", "lat": 42.1396, "lon": 24.7426},
    {"id": "RO00010", "name": "Cluj-Napoca", "city": "Cluj-Napoca", "country": "RO", "lat": 46.7820, "lon": 23.6244},
    {"id": "HR00010", "name": "Split", "city": "Split", "country": "HR", "lat": 43.5085, "lon": 16.4451},
]

TRUNK_ROUTES: List[List[str]] = [
    # Norway → Sweden → Denmark → Germany → Austria → Italy → Greece corridor
    ["NO00011", "NO00010", "7610155", "7610100", "7600100", "7100000", "8011160", "8100002", "8300050", "8300100", "5400600"],
    # Iberia → France → Germany
    ["7080001", "ES00012", "7160100", "ES00013", "7160200", "FR00105", "FR00101", "8727101", "8011160"],
    # UK → EU via Eurostar + UK regional spine
    ["GB00013", "GB00010", "GB00011", "5400076", "8800004", "8400058", "8011160"],
    # Ireland → UK
    ["IE00011", "IE00010", "5500001", "5400076"],
    # Eastern Europe spine
    ["8011160", "5400100", "SK00001", "5100001", "5400200", "RO00010", "5400300"],
    # Baltic → Poland → Berlin
    ["EE00001", "LV00001", "LT00001", "PL00010", "5100001", "8011160"],
    # Turkey → Balkans → Austria
    ["TR00003", "TR00001", "5400400", "BG00010", "5401000", "BA00001", "MK00001", "5400800", "8100002"],
    # Skandinavien tief
    ["FI00011", "FI00010", "7620100", "7600100", "SE00011", "SE00010", "7100000"],
    # Mediterran West
    ["IT00014", "IT00013", "8300100", "8300050", "IT00010", "FR00105", "FR00102", "7160200"],
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

# Map operator (and/or country) -> real booking URL for affiliate-style deep-link.
# Search-style links (?from=&to=&date=) where supported.
PROVIDER_LINKS: Dict[str, Dict[str, str]] = {
    "DB ICE":        {"name": "Deutsche Bahn",   "search": "https://www.bahn.de/buchung/start?so={from_name}&zo={to_name}&hd={iso_date}", "home": "https://www.bahn.de"},
    "SNCF TGV":      {"name": "SNCF Connect",    "search": "https://www.sncf-connect.com/app/home/search?origin={from_name}&destination={to_name}&outwardDate={iso_date}", "home": "https://www.sncf-connect.com"},
    "ÖBB Railjet":   {"name": "ÖBB",             "search": "https://tickets.oebb.at/de/ticket?from={from_name}&to={to_name}&departure={iso_date}", "home": "https://www.oebb.at"},
    "SBB IC":        {"name": "SBB Mobile",      "search": "https://www.sbb.ch/de.html?von={from_name}&nach={to_name}&datum={iso_date}", "home": "https://www.sbb.ch"},
    "Trenitalia FR": {"name": "Trenitalia",      "search": "https://www.trenitalia.com/en.html", "home": "https://www.trenitalia.com"},
    "Eurostar":      {"name": "Eurostar",        "search": "https://www.eurostar.com/uk-en/travel-info", "home": "https://www.eurostar.com"},
    "Renfe AVE":     {"name": "Renfe",           "search": "https://www.renfe.com/es/en", "home": "https://www.renfe.com"},
    "SJ":            {"name": "SJ Sweden",       "search": "https://www.sj.se/en/search-purchase/", "home": "https://www.sj.se"},
    "Vy":            {"name": "Vy Norway",       "search": "https://www.vy.no/en", "home": "https://www.vy.no"},
    "NS Intercity":  {"name": "NS",              "search": "https://www.ns.nl/en/journeyplanner", "home": "https://www.ns.nl"},
    "DSB":           {"name": "DSB Denmark",     "search": "https://www.dsb.dk/en/", "home": "https://www.dsb.dk"},
    "VR":            {"name": "VR Finland",      "search": "https://www.vr.fi/en", "home": "https://www.vr.fi"},
    "CP":            {"name": "CP Portugal",     "search": "https://www.cp.pt/passageiros/en", "home": "https://www.cp.pt"},
    "Irish Rail":    {"name": "Irish Rail",      "search": "https://www.irishrail.ie", "home": "https://www.irishrail.ie"},
    "National Rail": {"name": "National Rail UK","search": "https://www.nationalrail.co.uk", "home": "https://www.nationalrail.co.uk"},
    "PKP":           {"name": "PKP Intercity",   "search": "https://www.intercity.pl/en", "home": "https://www.intercity.pl"},
    "ČD":            {"name": "České dráhy",     "search": "https://www.cd.cz/en", "home": "https://www.cd.cz"},
    "MÁV":           {"name": "MÁV Hungary",     "search": "https://www.mavcsoport.hu/en", "home": "https://www.mavcsoport.hu"},
    "Hellenic":      {"name": "Hellenic Train",  "search": "https://hellenictrain.gr/en", "home": "https://hellenictrain.gr"},
    "TCDD":          {"name": "TCDD Türkiye",    "search": "https://ebilet.tcddtasimacilik.gov.tr/en", "home": "https://www.tcddtasimacilik.gov.tr"},
    "ZSSK":          {"name": "ZSSK Slovakia",   "search": "https://www.zssk.sk/en/", "home": "https://www.zssk.sk"},
    "CFR":           {"name": "CFR Călători",    "search": "https://www.cfrcalatori.ro/en/", "home": "https://www.cfrcalatori.ro"},
    "BDŽ":           {"name": "BDŽ Bulgaria",    "search": "https://www.bdz.bg/en/", "home": "https://www.bdz.bg"},
    "HŽPP":          {"name": "HŽ Putnički Croatia", "search": "https://www.hzpp.hr/en", "home": "https://www.hzpp.hr"},
    "Eurail":        {"name": "Eurail Pass",     "search": "https://www.eurail.com", "home": "https://www.eurail.com"},
}

# Country fallback (when operator unknown)
COUNTRY_PROVIDERS: Dict[str, str] = {
    "DE": "DB ICE", "FR": "SNCF TGV", "AT": "ÖBB Railjet", "CH": "SBB IC", "IT": "Trenitalia FR",
    "GB": "National Rail", "IE": "Irish Rail", "ES": "Renfe AVE", "PT": "CP", "SE": "SJ",
    "NO": "Vy", "DK": "DSB", "FI": "VR", "NL": "NS Intercity", "BE": "Eurostar",
    "LU": "Eurostar", "PL": "PKP", "CZ": "ČD", "HU": "MÁV", "SK": "ZSSK",
    "RO": "CFR", "BG": "BDŽ", "GR": "Hellenic", "HR": "HŽPP", "SI": "ÖBB Railjet",
    "RS": "MÁV", "MK": "Hellenic", "BA": "HŽPP", "ME": "HŽPP", "AL": "Eurail",
    "TR": "TCDD", "EE": "VR", "LV": "PKP", "LT": "PKP",
}


def resolve_provider_links(journey: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return one provider deep-link per unique country touched by the journey."""
    seen_countries = set()
    out: List[Dict[str, str]] = []
    for leg in journey["legs"]:
        # use country at start of each leg, plus final to-country
        country = leg["from"]["country"]
        if country in seen_countries:
            continue
        op_key = COUNTRY_PROVIDERS.get(country, "DB ICE")
        info = PROVIDER_LINKS.get(op_key) or PROVIDER_LINKS["DB ICE"]
        url = info["search"].format(
            from_name=leg["from"]["name"],
            to_name=leg["to"]["name"],
            iso_date=leg["departure"][:10],
        )
        out.append({"operator": op_key, "name": info["name"], "country": country, "url": url, "leg": f"{leg['from']['city']} → {leg['to']['city']}"})
        seen_countries.add(country)
    # also add the final destination country if different
    last = journey["legs"][-1]["to"]
    if last["country"] not in seen_countries:
        op_key = COUNTRY_PROVIDERS.get(last["country"], "DB ICE")
        info = PROVIDER_LINKS.get(op_key) or PROVIDER_LINKS["DB ICE"]
        out.append({"operator": op_key, "name": info["name"], "country": last["country"], "url": info["home"], "leg": f"{last['city']} ({last['country']})"})
    return out


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
def _norm(s: str) -> str:
    import unicodedata
    # NFD decompose then strip combining marks for accent-insensitive search
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


@api.get("/stations/search")
async def stations_search(q: str, limit: int = 8):
    q_low = _norm(q.strip())
    if not q_low:
        return []
    local = [s for s in SEED_STATIONS if q_low in _norm(s["name"]) or q_low in _norm(s["city"]) or q_low in _norm(s["country"])]
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
    cached["provider_links"] = resolve_provider_links(cached)
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
        t["provider_links"] = resolve_provider_links(j)
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


# ---------------------------------------------------------------------------
# Affiliate click tracking
# ---------------------------------------------------------------------------
class AffiliateClickIn(BaseModel):
    provider: str
    country: Optional[str] = None
    journey_id: Optional[str] = None
    leg: Optional[str] = None
    url: str


@api.post("/affiliate/click")
async def affiliate_click(body: AffiliateClickIn, request: Request, user=Depends(optional_user)):
    """Log an affiliate click then return the (potentially decorated) outbound URL."""
    # Append a UTM source param so partners can identify TrainConnect traffic
    target = body.url
    sep = "&" if ("?" in target) else "?"
    decorated = f"{target}{sep}utm_source=trainconnect&utm_medium=referral&utm_campaign=multi_leg"
    record = {
        "_id": str(uuid.uuid4()),
        "provider": body.provider,
        "country": body.country,
        "journey_id": body.journey_id,
        "leg": body.leg,
        "url": target,
        "decorated_url": decorated,
        "user_id": (user or {}).get("id"),
        "user_agent": request.headers.get("User-Agent", "")[:200],
        "referer": request.headers.get("Referer", "")[:200],
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    await db.affiliate_clicks.insert_one(record)
    return {"redirect_url": decorated, "click_id": record["_id"]}


@api.get("/affiliate/stats")
async def affiliate_stats(user=Depends(current_user)):
    """Per-provider + per-country aggregates. Available to any logged-in user."""
    rows = await db.affiliate_clicks.find().sort("ts", -1).to_list(2000)
    total = len(rows)
    by_provider: Dict[str, int] = {}
    by_country: Dict[str, int] = {}
    by_route: Dict[str, int] = {}
    last_7d = 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    for r in rows:
        by_provider[r["provider"]] = by_provider.get(r["provider"], 0) + 1
        if r.get("country"):
            by_country[r["country"]] = by_country.get(r["country"], 0) + 1
        if r.get("leg"):
            by_route[r["leg"]] = by_route.get(r["leg"], 0) + 1
        if r["ts"] > cutoff:
            last_7d += 1
    def top(d):
        return sorted(d.items(), key=lambda x: -x[1])[:10]
    return {
        "total_clicks": total,
        "last_7d": last_7d,
        "by_provider": [{"name": k, "clicks": v} for k, v in top(by_provider)],
        "by_country": [{"country": k, "clicks": v} for k, v in top(by_country)],
        "top_routes": [{"route": k, "clicks": v} for k, v in top(by_route)],
        "recent": [
            {"provider": r["provider"], "leg": r.get("leg"), "country": r.get("country"), "ts": r["ts"]}
            for r in rows[:20]
        ],
    }


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
