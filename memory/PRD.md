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

### Verbesserungen 1–5 (aus Analyse)
- ✅ Kaputter `port/5000`-Build-Bug eliminiert (sauberer Vite/CRA-Build mit `REACT_APP_BACKEND_URL`)
- ✅ Perplexity-Inline-Script entfernt
- ✅ Leaflet via npm gebundlet; CSS-CDN mit **SRI-Hash**
- ✅ PWA-Manifest auf 2026-Stand: getrennte `any`/`maskable` purposes, `id`, echte iOS-Icon (180×180), OG-Banner 1200×630, App-Shortcuts (Suchen / Tickets / Karte)
- ✅ Service-Worker mit `tc-2026-01-29` Cache-Version, **Network-First** für Navigations / HTML, Cache-First nur für gehashte Assets, `/api/*` nie gecached
- ✅ Code-Splitting / kein bloated single-bundle: CRA macht das automatisch, MapLibre/Leaflet sauber importiert
- ✅ Fonts via Preconnect + Fontshare (Cabinet Grotesk) statt @import (kein render-blocking)

### Shop / Booking-Plattform (Punkt 6)
- ✅ **Auth** (Register/Login/Me) mit JWT
- ✅ **Stations** (53 EU-Bahnhöfe seeded, Autocomplete-Search, transport.rest-Fallback)
- ✅ **Live-Abfahrten** pro Bahnhof (transport.rest live wenn verfügbar, sonst kuratiert)
- ✅ **Journey Search** Multi-Leg über trunk-routes (Stavanger → Athen → 8 Legs across NO/SE/DK/DE/AT/IT/GR)
- ✅ **Journey Detail** mit Etappen-Timeline (Pünktlich/+min Badges) + Live-Karte
- ✅ **Live-Position** des Zugs auf Karte (alle 30s aktualisiert)
- ✅ **OpenRailwayMap-Overlay** auf dunkler CartoDB-Karte
- ✅ **Multi-Leg-Warenkorb** (LocalStorage + serverseitige Cart)
- ✅ **Stripe Test-Checkout** (echte cs_test_-Session, polling /payments/v1/checkout/status/{id})
- ✅ **Ticket-PDF** via fpdf2 (mit Demo-Hinweis)
- ✅ **Meine Tickets** Seite mit PDF-Download
- ✅ PWA installierbar (Manifest + SW)

### Testing
- ✅ Testing-Agent: 19/19 Backend-Tests ✓, 100% Frontend ✓
- ✅ Infinite-Loop-Bug in /search behoben (useMemo für stabilen departure-Key)
- ✅ Stavanger → Athen E2E: 4 Optionen, 8 Legs, €480, OpenRailwayMap visualisiert

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
