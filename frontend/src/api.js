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
};

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
