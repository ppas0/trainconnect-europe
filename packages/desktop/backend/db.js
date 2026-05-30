/**
 * JSON-Datei-basierte Datenbank (drop-in für PostgreSQL)
 */
const fs   = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, 'data', 'db.json');

function loadDB() {
  if (!fs.existsSync(DB_PATH)) {
    fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
    const init = {
      users: [], tickets: [], carts: [], sessions: [],
      affiliateClicks: [], affiliateConfig: [], priceAlerts: [],
      pushSubscriptions: [], errors: [],
      meta: { version: '1.7', created: new Date().toISOString() }
    };
    fs.writeFileSync(DB_PATH, JSON.stringify(init, null, 2));
    return init;
  }
  return JSON.parse(fs.readFileSync(DB_PATH, 'utf8'));
}
function saveDB(db) {
  fs.writeFileSync(DB_PATH, JSON.stringify(db, null, 2));
}

// In-memory journey cache (journeys are generated on the fly, cached for lookup)
const journeyCache = new Map();
const CACHE_TTL = 4 * 60 * 60 * 1000; // 4h

const journeys = {
  store(journey) {
    journeyCache.set(journey.id, { journey, ts: Date.now() });
    // cleanup old entries
    if (journeyCache.size > 2000) {
      const now = Date.now();
      for (const [id, entry] of journeyCache) {
        if (now - entry.ts > CACHE_TTL) journeyCache.delete(id);
      }
    }
    return journey;
  },
  find(id) {
    const entry = journeyCache.get(id);
    if (!entry) return null;
    if (Date.now() - entry.ts > CACHE_TTL) { journeyCache.delete(id); return null; }
    return entry.journey;
  },
  storeMany(list) { list.forEach(j => this.store(j)); return list; },
};

// ── USERS ──────────────────────────────────────────────────────────────────────
const users = {
  findByEmail: e  => loadDB().users.find(u => u.email === e.toLowerCase()) || null,
  findById:    id => loadDB().users.find(u => u.id === id) || null,
  create(data) {
    const db = loadDB();
    const user = {
      id: uuidv4(), email: data.email.toLowerCase(),
      passwordHash: data.passwordHash, name: data.name,
      role: 'user', createdAt: new Date().toISOString(), loyaltyPoints: 0,
    };
    db.users.push(user); saveDB(db); return user;
  },
  update(id, patch) {
    const db = loadDB();
    const u = db.users.find(u => u.id === id);
    if (u) { Object.assign(u, patch); saveDB(db); }
    return u || null;
  },
  all: () => loadDB().users,
};

// ── TICKETS ────────────────────────────────────────────────────────────────────
const tickets = {
  create(data) {
    const db = loadDB();
    const ticket = {
      id:         uuidv4(),
      pnr:        'TC-' + Math.random().toString(36).toUpperCase().slice(2, 8),
      userId:     data.userId,
      from:       data.from,
      to:         data.to,
      fromId:     data.fromId,
      toId:       data.toId,
      departure:  data.departure,
      arrival:    data.arrival,
      passengers: data.passengers || 1,
      price:      data.price,
      operator:   data.operator,
      trainNo:    data.trainNo,
      status:     'confirmed',
      journeyId:  data.journeyId,
      legs:       data.legs || [],
      createdAt:  new Date().toISOString(),
    };
    db.tickets.push(ticket); saveDB(db); return ticket;
  },
  findByUser: userId => loadDB().tickets.filter(t => t.userId === userId)
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)),
  findById: id => loadDB().tickets.find(t => t.id === id) || null,
  all: () => loadDB().tickets,
};

// ── CARTS ──────────────────────────────────────────────────────────────────────
const carts = {
  create(data) {
    const db = loadDB();
    const cart = {
      id: uuidv4(), userId: data.userId,
      items: data.items, // [{journey_id, passengers}]
      status: 'open', createdAt: new Date().toISOString(),
    };
    db.carts.push(cart); saveDB(db); return cart;
  },
  findById: id => loadDB().carts.find(c => c.id === id) || null,
  update(id, patch) {
    const db = loadDB();
    const c = db.carts.find(c => c.id === id);
    if (c) { Object.assign(c, patch); saveDB(db); }
    return c || null;
  },
};

// ── CHECKOUT SESSIONS ──────────────────────────────────────────────────────────
const sessions = {
  create(data) {
    const db = loadDB();
    const sess = {
      id: 'SESS-' + uuidv4().slice(0, 12).toUpperCase(),
      cartId: data.cartId, userId: data.userId,
      payment_status: 'paid', status: 'complete',
      createdAt: new Date().toISOString(),
    };
    db.sessions.push(sess); saveDB(db); return sess;
  },
  findById: id => loadDB().sessions.find(s => s.id === id) || null,
};

// ── AFFILIATE ──────────────────────────────────────────────────────────────────
const affiliate = {
  addClick(data) {
    const db = loadDB();
    db.affiliateClicks.push({ id: uuidv4(), ...data, ts: new Date().toISOString() });
    if (db.affiliateClicks.length > 5000) db.affiliateClicks = db.affiliateClicks.slice(-5000);
    saveDB(db); return true;
  },
  getClicks: () => loadDB().affiliateClicks,
  getConfig(providers) {
    const db = loadDB();
    return providers.map(p => {
      const saved = db.affiliateConfig.find(c => c.provider === p.provider);
      return { ...p, affiliate_id: saved?.affiliate_id || null };
    });
  },
  saveConfig(provider, affiliate_id) {
    const db = loadDB();
    const idx = db.affiliateConfig.findIndex(c => c.provider === provider);
    if (idx >= 0) db.affiliateConfig[idx].affiliate_id = affiliate_id;
    else db.affiliateConfig.push({ provider, affiliate_id });
    saveDB(db);
  },
};

// ── PRICE ALERTS ───────────────────────────────────────────────────────────────
const priceAlerts = {
  create(data) {
    const db = loadDB();
    const alert = {
      id: uuidv4(), userId: data.userId,
      from_id: data.from_id, to_id: data.to_id,
      from_city: data.from_city || data.from_id,
      to_city:   data.to_city   || data.to_id,
      threshold: data.threshold, passengers: data.passengers || 1,
      last_price: null, active: true, createdAt: new Date().toISOString(),
    };
    db.priceAlerts.push(alert); saveDB(db); return alert;
  },
  findByUser: userId => loadDB().priceAlerts.filter(a => a.userId === userId),
  delete(id) {
    const db = loadDB();
    db.priceAlerts = db.priceAlerts.filter(a => a.id !== id);
    saveDB(db);
  },
  updateLastPrice(id, price) {
    const db = loadDB();
    const a = db.priceAlerts.find(a => a.id === id);
    if (a) { a.last_price = price; saveDB(db); }
  },
};

// ── PUSH SUBSCRIPTIONS ─────────────────────────────────────────────────────────
const push = {
  subscribe(data) {
    const db = loadDB();
    const existing = db.pushSubscriptions.findIndex(s => s.endpoint === data.endpoint);
    if (existing >= 0) db.pushSubscriptions[existing] = { ...data, createdAt: new Date().toISOString() };
    else db.pushSubscriptions.push({ id: uuidv4(), ...data, createdAt: new Date().toISOString() });
    saveDB(db);
  },
  unsubscribe(endpoint) {
    const db = loadDB();
    db.pushSubscriptions = db.pushSubscriptions.filter(s => s.endpoint !== endpoint);
    saveDB(db);
  },
  all: () => loadDB().pushSubscriptions,
};

// ── ERRORS ─────────────────────────────────────────────────────────────────────
const errors = {
  log(data) {
    const db = loadDB();
    db.errors.push({ id: uuidv4(), ...data, ts: new Date().toISOString() });
    if (db.errors.length > 200) db.errors = db.errors.slice(-200);
    saveDB(db);
  },
};

module.exports = { users, tickets, carts, sessions, affiliate, priceAlerts, push, errors, journeys };
