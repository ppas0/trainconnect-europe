# TrainConnect Europe – PRD

## Original Problem Statement
User uploaded `TrainConnect Europe v1.3.zip` (PWA production build). Asked for:
1. Analyse + Verbesserungen → Auflisten und umsetzen (Punkte 1–5)
2. Vollständiger **Shop** für ganz Europa: alle Zugverbindungen zeitnah, ein/mehrere Tickets buchen (z. B. Stavanger → Athen), alle Verspätungen, alle Bahnhöfe, **Live-Position des Zugs auf einer Karte** (à la "Google Maps für die Bahn"), sofort kaufbar.

Constraints: alles **kostenlos**, **echte Daten** wo möglich, **Test-Zahlung** (kein echtes Geld), kostenloses + sicheres Hosting empfohlen.

## Tech Stack
- Frontend: React 19 (CRA + craco), TailwindCSS, React-Router, Leaflet + react-leaflet, @phosphor-icons/react, Tanstack Query, Cabinet Grotesk + IBM Plex
- Backend: FastAPI, motor (async MongoDB), httpx, fpdf2, PyJWT, bcrypt
- Data: transport.rest (HAFAS-Proxy, free) + 53 kuratierter EU-Bahnhöfe Seed + Trunk-Routen für Cross-Border
- Maps: Leaflet + CartoDB Dark Matter Tiles + **OpenRailwayMap** Overlay (echte Schienen)
- Payments: Stripe **Test Mode** via `emergentintegrations` (`sk_test_emergent`)
- PWA: Manifest mit separaten icon-purposes, Service Worker mit Versions-Cache + network-first für HTML

## User Personas
- **Bahn-Reisende** (Hauptziel): vergleicht Verbindungen, sieht Live-Position, bucht 1–N Tickets
- **Gast-Nutzer**: kann ohne Account suchen, muss zum Buchen ein Konto haben (Tickets sind kontogebunden)
- **Admin** (Backlog): `/api/admin/stats` für Auslastung & Errors

## What's Been Implemented (Jan 2026)

### Phase 3 (29.01.2026) – Affiliate Tracking
- ✅ **POST /api/affiliate/click** – loggt jeden Klick in MongoDB-Collection `affiliate_clicks` (provider, country, journey_id, leg, user_agent, referer, ts, optional user_id). Hängt automatisch `utm_source=trainconnect&utm_medium=referral&utm_campaign=multi_leg` an die Ziel-URL.
- ✅ **GET /api/affiliate/stats** – aggregiert Total-Klicks, Last-7d, top_providers, by_country, top_routes, recent[20] (auth required).
- ✅ **ProviderLink** Component – ersetzt direkten Anchor: postet erst /affiliate/click, dann `window.open(decorated_url)`. Robuster Fallback bei Network-Fail.
- ✅ **AffiliateDashboard** Page (`/affiliate`) – KPI-Cards (Total, 7d, Anbieter, Länder) + 3 Tabellen (Top Anbieter, Top Länder, Top Strecken) + Letzte Klicks Liste, refetched alle 30s.
- ✅ **Header-Link "Analytics"** sichtbar, sobald User eingeloggt ist.
- ✅ Testing: **34/34 Backend pytest** + **100% Frontend** (Iteration 3) – keine Bugs gefunden.

### Phase 2 (29.01.2026) – Erweiterungen
- ✅ **+60 Bahnhöfe** seeded → jetzt **114 Stationen in 34 Ländern** (inkl. TR, BA, MK, AL, ME, EE, LV, LT, SK, BG, RO, HR + DE/FR/IT/ES/UK regional tiefer)
- ✅ **+4 trunk routes** für Cross-Border-Multi-Leg (Türkei→Balkan, Iberia tiefer, Baltikum, Mediterran West)
- ✅ **Provider Deep-Links** je nach Land: Vy, SJ, DSB, DB, ÖBB, SBB, SNCF, NS, Trenitalia, Renfe, CP, Hellenic Train, TCDD, PKP, ČD, MÁV, ZSSK, CFR, BDŽ, HŽPP, Irish Rail, National Rail UK, Eurostar, Eurail Pass (24 Operators gemappt zu 34 Ländern via COUNTRY_PROVIDERS). Auf Journey-Detail-Page sichtbar als "Direkt beim Anbieter buchen"-Sektion.
- ✅ **i18n DE/EN/FR/IT/ES** mit Sprach-Switcher im Header, persistiert in localStorage (`tc_lang`), aktualisiert `<html lang>` dynamisch, browser-Sprache wird als initial guess genutzt. ~70 Translation-Keys.
- ✅ **Bug fix**: Türkisches `İ` (U+0130) lowercased zu `i̇` (i + combining dot) → Stationssuche nach "istanbul" matched nicht. Fix: NFD-Normalisierung + Strip-Combining-Marks im `_norm()`-Helper.

### Phase 1 (initial)
- ✅ Verbesserungen 1–5 (kaputter Build-Bug, Inline-Script, SRI für Leaflet, PWA-Manifest, Service-Worker)
- ✅ Auth JWT (Register/Login/Me)
- ✅ Station Autocomplete + Live-Abfahrten
- ✅ Multi-Leg Journey Search inkl. Stavanger→Athen (8 Legs)
- ✅ Live-Karte mit OpenRailwayMap-Schienen + pulsierender Train-Marker
- ✅ Multi-Leg-Warenkorb + Stripe Test Checkout + PDF-Tickets
- ✅ Testing: Iteration 1 = 19/19 Backend + 100% Frontend, Iteration 2 = 27/27 Backend + 100% Frontend ✅

## Prioritized Backlog
- **P1** Echte Buchungs-API via Distribusion / Trainline Partner Solutions (kostenpflichtig, sobald Umsatz da)
- **P1** Sprache (i18n): EN/FR/IT/ES auf Basis von `lang`-Switcher (App spricht EU-Markt an)
- **P2** Live-Karte: tatsächliche `/trips/:id`-Position (statt simuliert) wenn transport.rest verfügbar
- **P2** Push-Notifications für Verspätungen (Web Push API)
- **P2** Apple/Google Wallet-Pass für Tickets (Public Domain `pass.json`-Generator)
- **P3** Admin-Dashboard UI (Backend gibt's, Frontend fehlt)
- **P3** Filter (Direktverbindungen, max. Umstiege, Klasse 1/2)
- **P3** Eurail/Interrail-Pass-Integration

## Free Hosting Recommendation
- **Frontend**: Cloudflare Pages (PWA-CDN, kostenlos, HTTPS, weltweit)
- **Backend + MongoDB**: Render.com Free oder Fly.io Free Tier (FastAPI + MongoDB Atlas Free)
- **Alternative**: alles auf Emergent-Preview-URL (für MVP-Tests reicht das)

## Next Action Items
1. User-Feedback einholen (Stripe Test-Card durchspielen, PDF prüfen)
2. Optional: Cloudflare Pages-Deployment vorbereiten (CRA-Build → `yarn build`)
3. Bei Bedarf: zweite Welle Stations seeden (Türkei, Balkan, Skandinavien tiefer)
