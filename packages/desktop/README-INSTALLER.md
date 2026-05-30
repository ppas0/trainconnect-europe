# TrainConnect Europe – Installer & Packaging

## Windows (.exe Installer) ✅ FERTIG
**Datei:** `dist/installer/TrainConnect-Europe-Setup-1.7.0.exe`

- Doppelklick auf die .exe → Installationsassistent
- Wähle Installationsverzeichnis
- Desktop- und Startmenü-Verknüpfung werden erstellt
- App startet automatisch nach Installation

**Neu bauen** (nach Code-Änderungen):
```bat
cd packages\desktop
node_modules\.bin\craco.cmd build  # React neu bauen
node create-icons.js                # Icons neu erstellen
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" trainconnect.iss
```

---

## macOS (.dmg) – Auf einem Mac bauen
```bash
cd packages/desktop
chmod +x build-mac.sh
./build-mac.sh
# Ergebnis: dist/installer/TrainConnect-Europe-1.7.0.dmg
```

**Voraussetzungen Mac:**
- macOS 12+ (Monterey oder neuer)
- Node.js 18+: `brew install node`
- Xcode Command Line Tools: `xcode-select --install`

---

## Android (.apk) – Mit Android Studio
**Verzeichnis:** `packages/mobile/android/`

```bash
# 1. Backend-URL für Gerät setzen (ersetze mit deiner PC-IP)
# Im Frontend: REACT_APP_BACKEND_URL=http://192.168.1.100:5000 npm run build
# Dann: npx cap sync

# 2. APK bauen
cd packages/mobile/android
./gradlew assembleDebug

# APK befindet sich in:
# android/app/build/outputs/apk/debug/app-debug.apk
```

**Android Studio öffnen:**
```bash
cd packages/mobile
npx cap open android
```

**Wichtig für Gerät-Tests:**
- Backend muss auf gleicher Netzwerk-IP laufen
- Ändere `capacitor.config.json`: 
  - Emulator: `http://10.0.2.2:5000`
  - Echtes Gerät: `http://DEINE_PC_IP:5000`

---

## iOS – Auf einem Mac mit Xcode
**Voraussetzungen:**
- Mac mit Xcode 15+
- Apple Developer Account (kostenlos für Testing, $99/Jahr für App Store)

```bash
# Auf dem Mac ausführen:
cd packages/mobile
npm install
npx cap add ios
npx cap sync ios
npx cap open ios
# Dann in Xcode: Build & Run
```

---

## PWA (Progressive Web App) – Alle Plattformen
Die App ist bereits als PWA konfiguriert (`manifest.json` + `sw.js`).

**Auf iOS/Android als PWA installieren:**
1. Öffne `http://DEINE_PC_IP:3000` im Mobile-Browser (Safari/Chrome)
2. "Zum Homescreen hinzufügen" (iOS) oder "App installieren" (Android)
3. Die App verhält sich wie eine native App

**Voraussetzung:** Backend (`start-backend.bat`) und Frontend (`start-frontend.bat`) müssen laufen.
