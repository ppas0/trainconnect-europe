try { require('dotenv').config(); } catch (_) {}
const express     = require('express');
const cors        = require('cors');
const helmet      = require('helmet');
const compression = require('compression');
const rateLimit   = require('express-rate-limit');
const path        = require('path');

const app  = express();
const PORT = process.env.PORT || 5000;

// ── SECURITY ──────────────────────────────────────────────────────────────────
app.use(helmet({ contentSecurityPolicy: false }));
app.use(compression());
app.use(cors({
  origin: (origin, cb) => cb(null, true),
  credentials: true,
}));
app.use(express.json({ limit: '2mb' }));

// ── RATE LIMITING ─────────────────────────────────────────────────────────────
app.use('/api/auth', rateLimit({ windowMs: 15*60*1000, max: 30, message: { detail: 'Zu viele Anfragen' } }));
app.use('/api',      rateLimit({ windowMs: 60*1000,    max: 300, message: { detail: 'API-Limit erreicht' } }));

// ── API ───────────────────────────────────────────────────────────────────────
app.use('/api', require('./routes'));

// ── STATIC FRONTEND (Production / Electron) ───────────────────────────────────
// Sucht das React-Build in mehreren möglichen Pfaden (Dev, Electron, Docker)
const STATIC_DIRS = [
  process.env.FRONTEND_BUILD_DIR,               // überschreibbar per ENV
  path.join(__dirname, '../frontend/build'),     // Entwicklung
  path.join(__dirname, 'public'),               // Produktion (kopiert)
  path.join(process.resourcesPath || '', 'frontend-build'), // Electron-Ressourcen
].filter(Boolean);

for (const dir of STATIC_DIRS) {
  try {
    if (require('fs').existsSync(path.join(dir, 'index.html'))) {
      app.use(express.static(dir));
      app.get('/{*filePath}', (req, res) => res.sendFile(path.join(dir, 'index.html')));
      console.log(`   → Serving frontend from: ${dir}`);
      break;
    }
  } catch (_) {}
}

// ── ERROR HANDLER ─────────────────────────────────────────────────────────────
app.use((err, req, res, next) => {
  console.error('[Error]', err.message);
  res.status(500).json({ detail: 'Interner Serverfehler' });
});

app.listen(PORT, () => {
  console.log(`\n🚆 TrainConnect Europe v1.7 – Backend`);
  console.log(`   → http://localhost:${PORT}/api/health`);
  console.log(`   → App:  http://localhost:${PORT}\n`);
});

module.exports = app;
