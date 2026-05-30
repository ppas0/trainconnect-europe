import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const TOKEN_KEY = "tc_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export const http = axios.create({ baseURL: API });
http.interceptors.request.use((cfg) => {
  const t = tokenStore.get();
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) tokenStore.clear();
    return Promise.reject(err);
  }
);

// ---- Auth ----
export const authApi = {
  register: (data) => http.post("/auth/register", data).then((r) => r.data),
  login: (data) => http.post("/auth/login", data).then((r) => r.data),
  me: () => http.get("/auth/me").then((r) => r.data),
};

// ---- Stations & Journeys ----
export const trainApi = {
  searchStations: (q) => http.get("/stations/search", { params: { q } }).then((r) => r.data),
  allStations: () => http.get("/stations").then((r) => r.data),
  stationDepartures: (id) => http.get(`/stations/${id}/departures`).then((r) => r.data),
  searchJourneys: (body) => http.post("/journeys/search", body).then((r) => r.data),
  journey: (id) => http.get(`/journeys/${id}`).then((r) => r.data),
  journeyLive: (id) => http.get(`/journeys/${id}/live`).then((r) => r.data),
  popular: () => http.get("/popular-routes").then((r) => r.data),
};

// ---- Cart & Checkout ----
export const cartApi = {
  create: (items) => http.post("/cart", items).then((r) => r.data),
  get: (id) => http.get(`/cart/${id}`).then((r) => r.data),
  checkout: (cart_id) =>
    http.post("/checkout/session", { cart_id, origin_url: window.location.origin }).then((r) => r.data),
  status: (sid) => http.get(`/payments/v1/checkout/status/${sid}`).then((r) => r.data),
};

// ---- Tickets ----
export const ticketsApi = {
  list: () => http.get("/tickets").then((r) => r.data),
  detail: (id) => http.get(`/tickets/${id}`).then((r) => r.data),
  pdfUrl: (id) => `${API}/tickets/${id}/pdf`,
  icsUrl: (id) => `${API}/tickets/${id}/ics`,
  pkpassUrl: (id) => `${API}/tickets/${id}/pkpass`,
};

// ---- Affiliate ----
export const affiliateApi = {
  trackClick: (data) => http.post("/affiliate/click", data).then((r) => r.data),
  stats: () => http.get("/affiliate/stats").then((r) => r.data),
  getConfig: () => http.get("/affiliate/config").then((r) => r.data),
  saveConfig: (data) => http.post("/affiliate/config", data).then((r) => r.data),
};

// ---- Push ----
export const pushApi = {
  publicKey: () => http.get("/push/public-key").then((r) => r.data.public_key),
  subscribe: (subscription) =>
    http.post("/push/subscribe", { endpoint: subscription.endpoint, keys: subscription.keys }).then((r) => r.data),
  unsubscribe: (endpoint) => http.post("/push/unsubscribe", { endpoint }).then((r) => r.data),
  test: () => http.post("/push/test").then((r) => r.data),
  notifyDelays: () => http.post("/push/notify-delays").then((r) => r.data),
};

// ---- Price Alerts ----
export const priceAlertsApi = {
  create: (data) => http.post("/price-alerts", data).then((r) => r.data),
  list: () => http.get("/price-alerts").then((r) => r.data),
  remove: (id) => http.delete(`/price-alerts/${id}`).then((r) => r.data),
  check: () => http.post("/price-alerts/check").then((r) => r.data),
};

// b64url -> Uint8Array (for VAPID applicationServerKey)
export function urlBase64ToUint8Array(b64) {
  const padding = "=".repeat((4 - (b64.length % 4)) % 4);
  const base64 = (b64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

// ---- helpers ----
export const fmtTime = (iso) => {
  try {
    return new Date(iso).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
  } catch { return "--:--"; }
};
export const fmtDate = (iso) => {
  try {
    return new Date(iso).toLocaleDateString("de-DE", { weekday: "short", day: "2-digit", month: "short" });
  } catch { return "—"; }
};
export const fmtDur = (min) => `${Math.floor(min / 60)}h ${min % 60}min`;
export const fmtPrice = (p) => `€ ${Number(p).toFixed(2)}`;
