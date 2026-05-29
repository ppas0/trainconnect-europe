/* TrainConnect Service Worker
 * - Cache version bumped on every deploy (placeholder replaced at build time)
 * - Network-first for navigations (HTML) -> always fresh app shell
 * - Cache-first for hashed /static/* assets -> fast & cheap
 * - Never cache /api/*
 */
const VERSION = "tc-2026-01-29";
const STATIC_CACHE = `tc-static-${VERSION}`;
const RUNTIME_CACHE = `tc-runtime-${VERSION}`;
const APP_SHELL = ["/", "/index.html", "/manifest.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(STATIC_CACHE).then((c) => c.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => ![STATIC_CACHE, RUNTIME_CACHE].includes(k)).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // Never cache the backend API
  if (url.pathname.startsWith("/api/")) return;

  // Network-first for navigations / index.html
  if (req.mode === "navigate" || req.destination === "document") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const clone = res.clone();
          caches.open(RUNTIME_CACHE).then((c) => c.put(req, clone));
          return res;
        })
        .catch(() => caches.match(req).then((r) => r || caches.match("/index.html")))
    );
    return;
  }

  // Cache-first for static hashed assets
  if (url.pathname.startsWith("/static/") || url.pathname.match(/\.(woff2?|ttf|png|jpg|jpeg|svg|webp|ico|css|js)$/)) {
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((res) => {
          if (res && res.status === 200 && res.type !== "opaque") {
            const clone = res.clone();
            caches.open(RUNTIME_CACHE).then((c) => c.put(req, clone));
          }
          return res;
        });
      })
    );
  }
});
