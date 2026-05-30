'use strict';

const { app, BrowserWindow, shell, Menu } = require('electron');
const path = require('path');
const http = require('http');
const fs   = require('fs');

// ── Konfiguration ─────────────────────────────────────────────────────────────
const IS_DEV = !app.isPackaged;
const PORT   = parseInt(process.env.PORT || '5000', 10);

// Pfade zum Frontend-Build und Backend
const APP_ROOT      = app.getAppPath();          // .asar oder Verzeichnis
const FRONTEND_DIR  = path.join(APP_ROOT, 'frontend-build');
const BACKEND_DIR   = path.join(APP_ROOT, 'backend');

let mainWindow = null;

// ── Backend starten ───────────────────────────────────────────────────────────
function startBackend() {
  try {
    // Datenbankverzeichnis sicherstellen (ausserhalb des App-Bundles)
    const dataDir = path.join(app.getPath('userData'), 'data');
    if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir, { recursive: true });

    process.env.PORT              = String(PORT);
    process.env.FRONTEND_BUILD_DIR = FRONTEND_DIR;
    process.env.NODE_ENV          = 'production';
    process.env.DB_PATH           = path.join(dataDir, 'db.json');

    // Backend-Code laden
    require(path.join(BACKEND_DIR, 'server.js'));
    console.log(`[TrainConnect] Backend gestartet auf Port ${PORT}`);
    console.log(`[TrainConnect] Frontend: ${FRONTEND_DIR}`);
    console.log(`[TrainConnect] Daten: ${dataDir}`);
  } catch (err) {
    console.error('[TrainConnect] Backend-Fehler:', err.message);
    throw err;
  }
}

// ── Auf Backend warten ────────────────────────────────────────────────────────
function waitForBackend(ms = 20000) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + ms;
    const check = () => {
      const req = http.get(`http://localhost:${PORT}/api/health`, (res) => {
        res.resume(); // consume response
        if (res.statusCode === 200) resolve(true);
        else retry();
      });
      req.on('error', retry);
      req.setTimeout(500, () => { req.destroy(); retry(); });
    };
    const retry = () => {
      if (Date.now() > deadline) return reject(new Error('Backend-Timeout nach 20s'));
      setTimeout(check, 500);
    };
    check();
  });
}

// ── Hauptfenster ──────────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width:   1280,
    height:  820,
    minWidth: 960,
    minHeight: 640,
    title:   'TrainConnect Europe',
    show:    false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(`http://localhost:${PORT}`)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    if (IS_DEV) mainWindow.webContents.openDevTools({ mode: 'detach' });
  });

  mainWindow.on('closed', () => { mainWindow = null; });
  mainWindow.loadURL(`http://localhost:${PORT}`);

  // Anwendungsmenü
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    {
      label: 'TrainConnect',
      submenu: [
        { label: 'Zurück', accelerator: 'Alt+Left', click: () => mainWindow?.webContents.goBack() },
        { label: 'Vor',   accelerator: 'Alt+Right', click: () => mainWindow?.webContents.goForward() },
        { label: 'Neu laden', accelerator: 'CmdOrCtrl+R', click: () => mainWindow?.reload() },
        { type: 'separator' },
        { label: 'Beenden', accelerator: 'Alt+F4', role: 'quit' },
      ],
    },
    {
      label: 'Ansicht',
      submenu: [
        { label: 'Vergrössern', accelerator: 'CmdOrCtrl+=', click: () => { const z = mainWindow?.webContents.getZoomFactor() || 1; mainWindow?.webContents.setZoomFactor(Math.min(z + 0.1, 2)); } },
        { label: 'Verkleinern', accelerator: 'CmdOrCtrl+-', click: () => { const z = mainWindow?.webContents.getZoomFactor() || 1; mainWindow?.webContents.setZoomFactor(Math.max(z - 0.1, 0.5)); } },
        { label: 'Normalgrösse', accelerator: 'CmdOrCtrl+0', click: () => mainWindow?.webContents.setZoomFactor(1) },
        { type: 'separator' },
        { label: 'Vollbild', accelerator: 'F11', click: () => mainWindow?.setFullScreen(!mainWindow.isFullScreen()) },
      ],
    },
    {
      label: 'Hilfe',
      submenu: [
        { label: 'Über TrainConnect Europe', click: () => {
          const { dialog } = require('electron');
          dialog.showMessageBox(mainWindow, {
            type: 'info', title: 'TrainConnect Europe',
            message: 'TrainConnect Europe v1.7.0',
            detail: 'Pan-Europäische Zugbuchungsplattform\nBerner Fachhochschule – Demo-Version\n\nDie Zahlungsabwicklung ist simuliert.\nKeine echten Buchungen.',
          });
        }},
      ],
    },
  ]));
}

// ── App-Start ─────────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  try {
    startBackend();
    await waitForBackend();
    createWindow();
  } catch (err) {
    const { dialog } = require('electron');
    dialog.showErrorBox('Startfehler', `TrainConnect konnte nicht gestartet werden:\n\n${err.message}\n\nStellen Sie sicher, dass Port ${PORT} frei ist.`);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (!mainWindow) createWindow();
});
