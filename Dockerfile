# TrainConnect Europe – Produktions-Docker-Image
# Fly.io / Docker Compose kompatibel
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile --network-timeout 300000

COPY frontend/ ./
RUN yarn build

# ── Produktions-Image ──────────────────────────────────────────────────────────
FROM node:20-alpine

WORKDIR /app

# Backend-Dependencies
COPY backend/package.json backend/package-lock.json ./backend/
RUN cd backend && npm ci --omit=dev

# Backend-Quellcode
COPY backend/ ./backend/

# React-Build aus dem Builder-Stage
RUN mkdir -p backend/public
COPY --from=frontend-builder /build/frontend/build/ ./backend/public/

# Datenbankverzeichnis anlegen (für persistenten Volume-Mount)
RUN mkdir -p backend/data && \
    echo '{"users":[],"tickets":[],"carts":[],"sessions":[],"affiliateClicks":[],"affiliateConfig":[],"priceAlerts":[],"pushSubscriptions":[],"errors":[],"meta":{"version":"1.7","created":"2026-01-01T00:00:00.000Z"}}' \
    > backend/data/db.json

EXPOSE 8080
ENV PORT=8080
ENV NODE_ENV=production

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD wget -qO- http://localhost:8080/api/health || exit 1

CMD ["node", "backend/server.js"]
