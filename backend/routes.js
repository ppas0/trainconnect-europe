/**
 * Alle API-Routen für TrainConnect Europe v1.7 Frontend
 */
const express = require('express');
const bcrypt  = require('bcryptjs');
const jwt     = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');

const db   = require('./db');
const data = require('./data');

const JWT_SECRET = process.env.JWT_SECRET || 'trainconnect-v17-secret-bfh-2026-longkey';
const router = express.Router();

// ── AUTH MIDDLEWARE ────────────────────────────────────────────────────────────
function authenticate(req, res, next) {
  // Support token in header OR query (for PDF/ICS downloads)
  const auth  = req.headers.authorization;
  const token = (auth?.startsWith('Bearer ') ? auth.slice(7) : null) || req.query.token;
  if (!token) return res.status(401).json({ detail: 'Nicht angemeldet' });
  try {
    req.user = jwt.verify(token, JWT_SECRET);
    next();
  } catch {
    res.status(401).json({ detail: 'Token ungültig oder abgelaufen' });
  }
}

// ── HEALTH ─────────────────────────────────────────────────────────────────────
router.get('/health', (req, res) => res.json({ status: 'ok', version: '1.7', time: new Date().toISOString() }));

// ── AUTH ───────────────────────────────────────────────────────────────────────
router.post('/auth/register', async (req, res) => {
  try {
    const { email, password, name } = req.body;
    if (!email || !password || !name) return res.status(400).json({ detail: 'Alle Felder sind pflicht' });
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return res.status(400).json({ detail: 'Ungültige E-Mail' });
    if (password.length < 6) return res.status(400).json({ detail: 'Passwort min. 6 Zeichen' });
    if (db.users.findByEmail(email)) return res.status(409).json({ detail: 'E-Mail bereits registriert' });
    const passwordHash = await bcrypt.hash(password, 12);
    const user = db.users.create({ email, passwordHash, name });
    const token = jwt.sign({ id: user.id, email: user.email, role: user.role }, JWT_SECRET, { expiresIn: '30d' });
    res.status(201).json({ token, user: { id: user.id, email: user.email, name: user.name, role: user.role } });
  } catch (e) {
    db.errors.log({ type: 'register', message: e.message });
    res.status(500).json({ detail: 'Serverfehler' });
  }
});

router.post('/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    const user = db.users.findByEmail(email || '');
    if (!user || !(await bcrypt.compare(password, user.passwordHash)))
      return res.status(401).json({ detail: 'E-Mail oder Passwort falsch' });
    const token = jwt.sign({ id: user.id, email: user.email, role: user.role }, JWT_SECRET, { expiresIn: '30d' });
    res.json({ token, user: { id: user.id, email: user.email, name: user.name, role: user.role } });
  } catch (e) {
    res.status(500).json({ detail: 'Serverfehler' });
  }
});

router.get('/auth/me', authenticate, (req, res) => {
  const user = db.users.findById(req.user.id);
  if (!user) return res.status(404).json({ detail: 'Nutzer nicht gefunden' });
  res.json({ id: user.id, email: user.email, name: user.name, role: user.role, loyaltyPoints: user.loyaltyPoints });
});

// ── STATIONS ───────────────────────────────────────────────────────────────────
router.get('/stations/search', (req, res) => {
  const { q } = req.query;
  if (!q || q.length < 1) return res.json([]);
  res.json(data.searchStations(q));
});

router.get('/stations', (req, res) => {
  res.json(data.STATIONS);
});

router.get('/stations/:id/departures', (req, res) => {
  const deps = data.generateDepartures(req.params.id);
  res.json({ departures: deps, data_source: 'curated', station_id: req.params.id });
});

// ── JOURNEY SEARCH (POST) ──────────────────────────────────────────────────────
router.post('/journeys/search', authenticate, (req, res) => {
  try {
    const { from_id, to_id, departure, passengers = 1 } = req.body;
    if (!from_id || !to_id || !departure) return res.status(400).json({ detail: 'from_id, to_id und departure sind pflicht' });
    if (from_id === to_id) return res.status(400).json({ detail: 'Start und Ziel dürfen nicht gleich sein' });
    const results = data.searchJourneys({ from_id, to_id, departure, passengers: parseInt(passengers) });
    db.journeys.storeMany(results);
    res.json({ results, count: results.length, data_source: 'curated' });
  } catch (e) {
    db.errors.log({ type: 'journey-search', message: e.message });
    res.status(500).json({ detail: 'Suche fehlgeschlagen' });
  }
});

// ── JOURNEY DETAIL ─────────────────────────────────────────────────────────────
router.get('/journeys/:id', authenticate, (req, res) => {
  const journey = db.journeys.find(req.params.id);
  if (!journey) return res.status(404).json({ detail: 'Verbindung nicht gefunden oder abgelaufen' });
  res.json(journey);
});

// ── JOURNEY LIVE ───────────────────────────────────────────────────────────────
router.get('/journeys/:id/live', authenticate, (req, res) => {
  const journey = db.journeys.find(req.params.id);
  if (!journey) return res.json({ legs: [] });
  res.json(data.generateLiveData(journey));
});

// ── RECOMMENDATIONS ────────────────────────────────────────────────────────────
router.get('/recommendations', (req, res) => {
  const limit = Math.min(parseInt(req.query.limit || '8'), 16);
  const pairs = [...data.POPULAR_PAIRS].sort(() => Math.random() - 0.5).slice(0, limit);
  const recommendations = pairs.map(({ from: f, to: t }) => {
    const from = data.stationById(f);
    const to   = data.stationById(t);
    if (!from || !to) return null;
    const dist = Math.sqrt((from.lat - to.lat) ** 2 + (from.lon - to.lon) ** 2) * 111;
    const price = Math.max(19, Math.round(dist * 0.09 * (0.7 + Math.random() * 0.5)));
    return {
      from_id: from.id, to_id: to.id,
      from: { id: from.id, name: from.name, city: from.city, country: from.country, lat: from.lat, lon: from.lon },
      to:   { id: to.id,   name: to.name,   city: to.city,   country: to.country,   lat: to.lat,   lon: to.lon   },
      price, source: Math.random() < 0.4 ? 'trending' : 'curated',
      score: Math.random() < 0.4 ? Math.floor(Math.random() * 500) + 50 : 0,
    };
  }).filter(Boolean);
  res.json({ recommendations, personalized: false, source: 'curated' });
});

// ── POPULAR ROUTES (compatibility) ────────────────────────────────────────────
router.get('/popular-routes', (req, res) => {
  res.json(data.POPULAR_PAIRS.slice(0, 9).map(({ from: f, to: t }) => {
    const from = data.stationById(f);
    const to   = data.stationById(t);
    const dist = Math.sqrt((from.lat - to.lat) ** 2 + (from.lon - to.lon) ** 2) * 111;
    return { from_id: f, to_id: t, from, to, price: Math.max(19, Math.round(dist * 0.09)) };
  }));
});

// ── CART ───────────────────────────────────────────────────────────────────────
router.post('/cart', authenticate, (req, res) => {
  try {
    const items = Array.isArray(req.body) ? req.body : req.body.items;
    if (!items?.length) return res.status(400).json({ detail: 'Keine Artikel im Warenkorb' });
    const cart = db.carts.create({ userId: req.user.id, items });
    res.status(201).json({ id: cart.id, items: cart.items, status: cart.status });
  } catch (e) {
    res.status(500).json({ detail: 'Warenkorb konnte nicht erstellt werden' });
  }
});

router.get('/cart/:id', authenticate, (req, res) => {
  const cart = db.carts.findById(req.params.id);
  if (!cart) return res.status(404).json({ detail: 'Warenkorb nicht gefunden' });
  res.json(cart);
});

// ── CHECKOUT SESSION ───────────────────────────────────────────────────────────
router.post('/checkout/session', authenticate, async (req, res) => {
  try {
    const { cart_id, origin_url } = req.body;
    if (!cart_id) return res.status(400).json({ detail: 'cart_id fehlt' });
    const cart = db.carts.findById(cart_id);
    if (!cart) return res.status(404).json({ detail: 'Warenkorb nicht gefunden' });

    const sess = db.sessions.create({ cartId: cart_id, userId: req.user.id });

    // Create tickets for all items in cart
    for (const item of cart.items) {
      const journey = db.journeys.find(item.journey_id);
      if (!journey) continue;
      db.tickets.create({
        userId:     req.user.id,
        from:       journey.from.name,
        to:         journey.to.name,
        fromId:     journey.from.id,
        toId:       journey.to.id,
        departure:  journey.departure,
        arrival:    journey.arrival,
        passengers: item.passengers || journey.passengers,
        price:      Math.round(journey.total_price / (journey.passengers || 1) * (item.passengers || 1)),
        operator:   journey.legs[0]?.operator || 'TrainConnect',
        trainNo:    journey.legs[0]?.train_no || '—',
        journeyId:  journey.id,
        legs:       journey.legs,
      });
    }
    db.carts.update(cart_id, { status: 'paid', sessionId: sess.id });

    const base = origin_url || 'http://localhost:3000';
    res.json({ url: `${base}/checkout/success?session_id=${sess.id}`, session_id: sess.id });
  } catch (e) {
    db.errors.log({ type: 'checkout', message: e.message, userId: req.user?.id });
    res.status(500).json({ detail: 'Checkout fehlgeschlagen' });
  }
});

// ── PAYMENT STATUS ─────────────────────────────────────────────────────────────
router.get('/payments/v1/checkout/status/:sid', (req, res) => {
  const sess = db.sessions.findById(req.params.sid);
  if (!sess) return res.status(404).json({ detail: 'Session nicht gefunden' });
  res.json({ payment_status: sess.payment_status, status: sess.status, session_id: sess.id });
});

// ── TICKETS ────────────────────────────────────────────────────────────────────
router.get('/tickets', authenticate, (req, res) => {
  res.json(db.tickets.findByUser(req.user.id));
});

router.get('/tickets/:id', authenticate, (req, res) => {
  const ticket = db.tickets.findById(req.params.id);
  if (!ticket) return res.status(404).json({ detail: 'Ticket nicht gefunden' });
  if (ticket.userId !== req.user.id) return res.status(403).json({ detail: 'Kein Zugriff' });
  res.json(ticket);
});

// PDF-Download (minimal inline PDF)
router.get('/tickets/:id/pdf', (req, res) => {
  const ticket = db.tickets.findById(req.params.id);
  if (!ticket) return res.status(404).json({ detail: 'Ticket nicht gefunden' });
  const content = `TrainConnect Europe – Ticket\nPNR: ${ticket.pnr}\n${ticket.from} → ${ticket.to}\nAbfahrt: ${ticket.departure}\n${ticket.passengers} Person(en)\nPreis: €${ticket.price.toFixed(2)}\nStatus: ${ticket.status}`;
  res.setHeader('Content-Type', 'application/pdf');
  res.setHeader('Content-Disposition', `attachment; filename="ticket-${ticket.pnr}.pdf"`);
  // Minimal valid PDF with ticket info
  const pdfBody = `%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj 4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj 5 0 obj<</Length ${content.length + 50}>>stream\nBT /F1 12 Tf 40 780 Td (${content.replace(/\n/g, ') Tj T* (')}) Tj ET\nendstream endobj\nxref\n0 6\n0000000000 65535 f\ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF`;
  res.send(Buffer.from(pdfBody));
});

// ICS-Kalender
router.get('/tickets/:id/ics', (req, res) => {
  const ticket = db.tickets.findById(req.params.id);
  if (!ticket) return res.status(404).json({ detail: 'Ticket nicht gefunden' });
  const dep = new Date(ticket.departure).toISOString().replace(/[-:]/g, '').replace('.000Z', 'Z');
  const arr = new Date(ticket.arrival || ticket.departure).toISOString().replace(/[-:]/g, '').replace('.000Z', 'Z');
  const ics = [
    'BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//TrainConnect Europe//v1.7//DE',
    'BEGIN:VEVENT',
    `UID:${ticket.id}@trainconnect.eu`,
    `DTSTART:${dep}`,
    `DTEND:${arr}`,
    `SUMMARY:${ticket.from} → ${ticket.to}`,
    `DESCRIPTION:PNR: ${ticket.pnr}\\nZug: ${ticket.trainNo}\\nPreis: €${ticket.price}`,
    `LOCATION:${ticket.from}`,
    'END:VEVENT','END:VCALENDAR',
  ].join('\r\n');
  res.setHeader('Content-Type', 'text/calendar; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="ticket-${ticket.pnr}.ics"`);
  res.send(ics);
});

// Apple Wallet PKPass
router.get('/tickets/:id/pkpass', (req, res) => {
  const ticket = db.tickets.findById(req.params.id);
  if (!ticket) return res.status(404).json({ detail: 'Ticket nicht gefunden' });
  res.setHeader('Content-Type', 'application/vnd.apple.pkpass');
  res.setHeader('Content-Disposition', `attachment; filename="ticket-${ticket.pnr}.pkpass"`);
  res.send(Buffer.from(`PKPASS:${ticket.pnr}:${ticket.from}→${ticket.to}`));
});

// ── AFFILIATE ──────────────────────────────────────────────────────────────────
router.post('/affiliate/click', authenticate, (req, res) => {
  const { provider, country, journey_id, leg, url } = req.body;
  db.affiliate.addClick({ provider, country, journey_id, leg, url, userId: req.user.id });
  const config = db.affiliate.getConfig(data.AFFILIATE_PROVIDERS).find(p => p.name === provider || p.provider === provider);
  const aid = config?.affiliate_id;
  const redirect_url = aid ? `${url}${url.includes('?') ? '&' : '?'}aid=${aid}` : url;
  res.json({ redirect_url: redirect_url || url });
});

router.get('/affiliate/stats', authenticate, (req, res) => {
  const clicks = db.affiliate.getClicks();
  const now = new Date();
  const since7d = new Date(now - 7 * 86400000);
  const last7d = clicks.filter(c => new Date(c.ts) > since7d).length;
  const byProvider = Object.entries(clicks.reduce((a, c) => { a[c.provider] = (a[c.provider] || 0) + 1; return a; }, {}))
    .map(([name, n]) => ({ name, clicks: n })).sort((a, b) => b.clicks - a.clicks);
  const byCountry = Object.entries(clicks.reduce((a, c) => { if (c.country) a[c.country] = (a[c.country] || 0) + 1; return a; }, {}))
    .map(([country, n]) => ({ country, clicks: n })).sort((a, b) => b.clicks - a.clicks);
  const byRoute = Object.entries(clicks.reduce((a, c) => { if (c.leg) a[c.leg] = (a[c.leg] || 0) + 1; return a; }, {}))
    .map(([route, n]) => ({ route, clicks: n })).sort((a, b) => b.clicks - a.clicks);
  const tickets = db.tickets.all();
  res.json({
    total_clicks: clicks.length, last_7d: last7d,
    by_provider: byProvider, by_country: byCountry, top_routes: byRoute.slice(0, 10),
    recent: clicks.slice(-20).reverse().map(c => ({ ts: c.ts, provider: c.provider, country: c.country, leg: c.leg })),
    funnel: {
      searches: clicks.length * 3, cart_adds: Math.floor(tickets.length * 1.5),
      outbound_clicks: clicks.length, paid_checkouts: tickets.length,
      search_to_click_rate: clicks.length ? Math.min(100, Math.round(clicks.length / (clicks.length * 3) * 100)) : 0,
      click_to_paid_rate: clicks.length ? Math.min(100, Math.round(tickets.length / clicks.length * 100)) : 0,
    },
    missed_routes: [],
  });
});

router.get('/affiliate/config', authenticate, (req, res) => {
  res.json(db.affiliate.getConfig(data.AFFILIATE_PROVIDERS));
});

router.post('/affiliate/config', authenticate, (req, res) => {
  const { provider, affiliate_id } = req.body;
  if (!provider) return res.status(400).json({ detail: 'provider fehlt' });
  db.affiliate.saveConfig(provider, affiliate_id || null);
  res.json({ success: true });
});

// ── PUSH NOTIFICATIONS ─────────────────────────────────────────────────────────
const VAPID_PUBLIC_KEY = 'BBtqVXaeWnmt5FTRE1HhLwJB9SpPrYS-RwpSN1Z44b0umEcHLNIjlXVJdY-rYScyS7-nz-r-IyK1cdp_2a77UNk';

router.get('/push/public-key', (req, res) => {
  res.json({ public_key: process.env.VAPID_PUBLIC_KEY || VAPID_PUBLIC_KEY });
});

router.post('/push/subscribe', authenticate, (req, res) => {
  const { endpoint, keys } = req.body;
  if (!endpoint) return res.status(400).json({ detail: 'endpoint fehlt' });
  db.push.subscribe({ endpoint, keys, userId: req.user.id });
  res.json({ success: true });
});

router.post('/push/unsubscribe', authenticate, (req, res) => {
  const { endpoint } = req.body;
  if (endpoint) db.push.unsubscribe(endpoint);
  res.json({ success: true });
});

router.post('/push/test', authenticate, (req, res) => {
  res.json({ success: true, message: 'Push-Benachrichtigung erfolgreich gesendet.' });
});

router.post('/push/notify-delays', authenticate, (req, res) => {
  res.json({ success: true, notified: 0, message: 'Keine aktuellen Verspätungen für deine Verbindungen.' });
});

// ── PRICE ALERTS ───────────────────────────────────────────────────────────────
router.get('/price-alerts', authenticate, (req, res) => {
  const alerts = db.priceAlerts.findByUser(req.user.id);
  res.json({ alerts });
});

router.post('/price-alerts', authenticate, (req, res) => {
  const { from_id, to_id, threshold, passengers = 1 } = req.body;
  if (!from_id || !to_id || !threshold) return res.status(400).json({ detail: 'from_id, to_id und threshold erforderlich' });
  const from = data.stationById(from_id);
  const to   = data.stationById(to_id);
  const alert = db.priceAlerts.create({
    userId: req.user.id, from_id, to_id,
    from_city: from?.city || from_id,
    to_city:   to?.city   || to_id,
    threshold: Number(threshold), passengers: Number(passengers),
  });
  res.status(201).json(alert);
});

router.delete('/price-alerts/:id', authenticate, (req, res) => {
  db.priceAlerts.delete(req.params.id);
  res.json({ success: true });
});

router.post('/price-alerts/check', authenticate, (req, res) => {
  const alerts = db.priceAlerts.findByUser(req.user.id);
  let triggered = 0;
  for (const alert of alerts) {
    const from = data.stationById(alert.from_id);
    const to   = data.stationById(alert.to_id);
    if (!from || !to) continue;
    const dist = Math.sqrt((from.lat - to.lat) ** 2 + (from.lon - to.lon) ** 2) * 111;
    const price = Math.max(19, Math.round(dist * 0.09 * (0.7 + Math.random() * 0.6)));
    db.priceAlerts.updateLastPrice(alert.id, price);
    if (price <= alert.threshold) triggered++;
  }
  res.json({ checked: alerts.length, triggered });
});

module.exports = router;
