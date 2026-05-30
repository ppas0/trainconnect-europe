#!/bin/bash
# TrainConnect Europe – macOS Build Script
# Ausführen auf einem Mac: chmod +x build-mac.sh && ./build-mac.sh
set -e

APP_NAME="TrainConnect Europe"
APP_VERSION="1.7.0"
BUNDLE_ID="eu.trainconnect.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo ""
echo "🚆 TrainConnect Europe – macOS Build"
echo "======================================"
echo ""

# --- Node.js prüfen ---
if ! command -v node &>/dev/null; then
    echo "❌ Node.js nicht gefunden. Installiere via: brew install node"
    exit 1
fi
echo "✅ Node.js $(node --version)"

# --- React Production Build ---
echo ""
echo "📦 Schritt 1: React Frontend bauen..."
cd "$ROOT_DIR/frontend"
if [ ! -f ".env.production" ]; then
    echo "REACT_APP_BACKEND_URL=" > .env.production
fi
CI=false npm run build
echo "✅ Frontend gebaut: $(find build -type f | wc -l | tr -d ' ') Dateien"

# --- Desktop Abhängigkeiten ---
echo ""
echo "📦 Schritt 2: Abhängigkeiten installieren..."
cd "$SCRIPT_DIR"
npm install

# --- Frontend-Build ins Desktop-Package kopieren ---
cp -r "$ROOT_DIR/frontend/build" "$SCRIPT_DIR/frontend-build"
echo "✅ Frontend-Build kopiert"

# --- Saubere App-Source ---
echo ""
echo "📦 Schritt 3: App-Bundle erstellen..."
APP_SRC="$SCRIPT_DIR/app-source-clean"
rm -rf "$APP_SRC"
mkdir -p "$APP_SRC"
cp main.js preload.js "$APP_SRC/"
cp -r backend frontend-build "$APP_SRC/"
cat > "$APP_SRC/package.json" <<EOF
{
  "name": "trainconnect-europe",
  "version": "$APP_VERSION",
  "main": "main.js",
  "dependencies": {
    "bcryptjs": "^3.0.3",
    "compression": "^1.8.1",
    "cors": "^2.8.6",
    "express": "^5.2.1",
    "express-rate-limit": "^8.5.2",
    "helmet": "^8.2.0",
    "jsonwebtoken": "^9.0.3",
    "uuid": "^14.0.0"
  }
}
EOF
cd "$APP_SRC"
npm install --omit=dev --quiet
echo "✅ App-Source: $(du -sh . | cut -f1)"

# --- Electron herunterladen ---
echo ""
echo "📦 Schritt 4: Electron für macOS herunterladen..."
cd "$SCRIPT_DIR"
ELECTRON_VER=$(node -e "console.log(require('./node_modules/electron/package.json').version)")
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    ELECTRON_ARCH="arm64"
else
    ELECTRON_ARCH="x64"
fi
ELECTRON_ZIP="electron-v${ELECTRON_VER}-darwin-${ELECTRON_ARCH}.zip"
ELECTRON_URL="https://github.com/electron/electron/releases/download/v${ELECTRON_VER}/${ELECTRON_ZIP}"

if [ ! -d "dist/mac/Electron.app" ]; then
    mkdir -p dist/mac
    echo "Lade $ELECTRON_ZIP herunter..."
    curl -L "$ELECTRON_URL" -o "/tmp/${ELECTRON_ZIP}"
    cd dist/mac
    unzip -q "/tmp/${ELECTRON_ZIP}"
    rm "/tmp/${ELECTRON_ZIP}"
    echo "✅ Electron $ELECTRON_VER (darwin-${ELECTRON_ARCH}) entpackt"
    cd "$SCRIPT_DIR"
fi

# --- app.asar erstellen ---
echo ""
echo "📦 Schritt 5: app.asar erstellen..."
node -e "
  require('@electron/asar').createPackage('$APP_SRC', 'dist/mac/Electron.app/Contents/Resources/app.asar')
    .then(() => console.log('✅ app.asar erstellt'))
    .catch(e => { console.error(e); process.exit(1); })
"

# --- Electron.app umbenennen ---
echo ""
echo "📦 Schritt 6: App umbenennen..."
APP_BUNDLE="dist/mac/${APP_NAME}.app"
mv "dist/mac/Electron.app" "$APP_BUNDLE"

# Name in Info.plist anpassen
PLIST="$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleName '${APP_NAME}'"           "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName '${APP_NAME}'"   "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier '${BUNDLE_ID}'"   "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString '${APP_VERSION}'" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion '${APP_VERSION}'"    "$PLIST"
echo "✅ App umbenannt: $APP_BUNDLE"

# --- DMG erstellen ---
echo ""
echo "📦 Schritt 7: DMG erstellen..."
DMG_OUT="dist/installer/${APP_NAME// /-}-${APP_VERSION}.dmg"
mkdir -p dist/installer
DMG_TMP="/tmp/trainconnect-dmg-$$"
mkdir -p "$DMG_TMP"
cp -r "$APP_BUNDLE" "$DMG_TMP/"
ln -s /Applications "$DMG_TMP/Applications"

hdiutil create \
    -volname "${APP_NAME} ${APP_VERSION}" \
    -srcfolder "$DMG_TMP" \
    -ov -format UDZO \
    -fs HFS+ \
    "$DMG_OUT"

rm -rf "$DMG_TMP"
echo ""
echo "✅ macOS DMG erstellt: $DMG_OUT"
echo "   Grösse: $(du -h "$DMG_OUT" | cut -f1)"
echo ""
echo "🎉 Build abgeschlossen!"
echo "   → $DMG_OUT"
echo ""
