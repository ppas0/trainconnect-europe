# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TrainConnect Europe v1.7 – a full-stack European train booking platform (BFH school project). React SPA frontend + Node.js/Express backend. Journey data is curated/generated (no live rail API dependency in production).

## Commands

### Backend (Node.js, port 5000)
```bash
cd backend
npm install          # first time only
npm start            # production
node server.js       # same thing
```

### Frontend (React/Craco, port 3000)
```bash
cd frontend
yarn install         # first time only (uses yarn)
yarn start           # dev server with hot-reload
yarn build           # production build → frontend/build/
yarn test            # run Jest tests
```

### Python tests (hit running backend via HTTP)
```bash
cd backend
pip install -r requirements.txt        # first time only
pytest tests/test_trainconnect.py -v   # main regression suite
pytest tests/ -v                       # all test files
# Point at a different backend:
REACT_APP_BACKEND_URL=http://localhost:5000 pytest tests/ -v
```

### Production (single process)
The Express backend serves the React build as static files. Copy `frontend/build/` to `backend/public/` **or** set `FRONTEND_BUILD_DIR` env var, then run `npm start` from `backend/`.

## Architecture

### Backend (`backend/`)
| File | Role |
|------|------|
| `server.js` | Express entry point, middleware (Helmet, CORS, rate-limiting), static file serving |
| `routes.js` | All API route handlers (`/api/*`) |
| `db.js` | Flat JSON "database" – reads/writes `data/db.json` on every call; in-memory journey cache (4 h TTL) |
| `data.js` | Static station list (~80 European cities with IATA-style IDs), operators, journey generation, live-data simulation |

**All persistence** is in `backend/data/db.json` (users, tickets, carts, sessions, affiliate clicks, price alerts, push subscriptions). There is no SQL or MongoDB dependency in the Node backend.

### Frontend (`frontend/src/`)
| File | Role |
|------|------|
| `App.js` | Router setup, provider composition (Lang → Auth → Cart → BrowserRouter) |
| `api.js` | Axios instance + all API wrappers (`authApi`, `trainApi`, `cartApi`, `ticketsApi`, `affiliateApi`, `pushApi`, `priceAlertsApi`) |
| `store.jsx` | React Context for auth (`AuthCtx`) and cart (`CartCtx`); JWT in `localStorage` under key `tc_token`; cart items under `tc_cart_items` |
| `pages.jsx` | All page components in one file: Home, Search, JourneyDetail, Stations, Cart, CheckoutSuccess, Tickets, AuthPage, AffiliateDashboard, PriceAlertsPage |
| `components.jsx` | Shared UI: SearchWidget, RouteMap (Leaflet), JourneyCard, StationsMap, DelayPill, ShareBar |
| `i18n.jsx` | Custom i18n – one `DICT` object, `useT()` hook, 5 languages (DE/EN/FR/IT/ES) |

**UI library**: shadcn/ui components (Radix UI primitives + Tailwind) live in `src/components/ui/`. Path alias `@` → `src/`.

### Request flow
1. Frontend calls `REACT_APP_BACKEND_URL` (env) + `/api/<endpoint>`
2. JWT sent as `Authorization: Bearer <token>` header
3. `routes.js` → `authenticate()` middleware → handler → `db.js` + `data.js`

### Checkout / "Demo Mode"
The checkout in `routes.js` (`POST /checkout/session`) immediately creates tickets and marks the cart `paid` without hitting Stripe. The `session.payment_status` is set to `"paid"` on creation. This is what the frontend polls to show the success screen.

### Two backends (historical)
`backend/server.py` is a FastAPI/Python version (uses MongoDB, Stripe, VAPID push). It is **not** used by the v1.7 frontend – the Node.js server (`server.js`) is the active backend.

## Environment Variables

### Backend (`backend/.env`)
```
MONGO_URL=        # not used by Node backend; only needed if running server.py
JWT_SECRET=       # change in production!
JWT_ALGORITHM=HS256
JWT_EXPIRE_MIN=10080
STRIPE_API_KEY=   # not used in demo mode
TRANSPORT_REST_BASE=https://v6.db.transport.rest
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY_FILE=
CORS_ORIGINS=*
```

### Frontend (`frontend/.env`)
```
REACT_APP_BACKEND_URL=http://localhost:5000   # empty string = same origin in prod build
REACT_APP_VAPID_PUBLIC_KEY=
```

In production: set `REACT_APP_BACKEND_URL=` (empty) so the SPA uses same-origin requests, and let the Node server serve the React build.

## Key Patterns

- **Journey IDs** are generated UUIDs, cached in memory for 4 h. They are NOT persisted to `db.json`, so they expire on server restart.
- **Station IDs** in `data.js` use short IATA-style codes (`BER`, `ZRH`, `CDG`…). The Python backend (`server.py`) uses numeric transport.rest IDs (`8011160`). Do not mix them.
- **Price calculation** uses Haversine approximation × €0.09/km with random ±30% variance; no real fare data.
- **Affiliate links** are deep-link URLs to external booking sites. Click tracking is stored in `db.json`.
- **Push notifications** subscribe/unsubscribe endpoints exist but actual web-push dispatch is a stub (`POST /push/test` always returns success without sending).
