# CIRO Mobile Installation Guide

## Overview
CIRO's mobile-first dashboard is packaged as a native Android APK using **CapacitorJS**. The app wraps the `static/index.html` web dashboard into an installable Android application with smart network detection and offline demo capabilities.

---

## Prerequisites

| Tool | Version | Purpose |
|:---|:---|:---|
| Node.js | 18+ | Package management |
| npm | 9+ | Dependency installation |
| Android Studio | Latest | APK compilation |
| Android SDK | API 24+ | Target platform |
| Java JDK | 17+ | Gradle builds |

---

## Step 1: Install Node Dependencies

```bash
cd karachi-flood-farheen_agents
npm install
```

This installs:
- `@capacitor/core` — Runtime bridge
- `@capacitor/android` — Android platform
- `@capacitor/cli` — Build tools

---

## Step 2: Add Android Platform

```bash
npx cap add android
```

This creates the `android/` directory with a standard Gradle project.

---

## Step 3: Sync Web Assets

After any changes to `static/index.html`:

```bash
npx cap sync android
```

This copies the `static/` directory into the Android native assets.

---

## Step 4: Build the APK

### Option A: Android Studio (Recommended)

```bash
npx cap open android
```

1. Wait for Gradle sync to complete.
2. Go to **Build** → **Build Bundle(s) / APK(s)** → **Build APK(s)**.
3. Find the APK at: `android/app/build/outputs/apk/debug/app-debug.apk`
4. Rename to `CIRO-Mobile-Demo.apk`

### Option B: Command Line

```bash
cd android
./gradlew assembleDebug
```

APK location: `android/app/build/outputs/apk/debug/app-debug.apk`

---

## Step 5: Install on Device

### Emulator
1. Drag and drop the APK onto the Android emulator window.

### Physical Device
1. Enable **Settings → Security → Unknown Sources** (or Install Unknown Apps for the file manager).
2. Transfer the APK via USB, ADB, or Google Drive.
3. Tap the APK to install.

```bash
# ADB install
adb install CIRO-Mobile-Demo.apk
```

---

## Network Configuration

### How the App Detects Backend

The app uses smart host detection at startup:

| Environment | Detected Host | Backend URL |
|:---|:---|:---|
| Browser (development) | `localhost:8000` | `http://localhost:8000` |
| Browser (deployed) | `window.location.host` | Dynamic |
| Android Emulator | `10.0.2.2:8000` | Emulator loopback to host |
| Physical Device (no backend) | — | **Offline Demo Mode** |

### Connecting a Physical Device to Local Backend

If testing on a physical device connected to the same WiFi:

1. Find your computer's local IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
2. In `static/index.html`, temporarily update `backendHost`:
   ```javascript
   backendHost = '192.168.1.XXX:8000';
   ```
3. Run `npx cap sync android` and rebuild.
4. Ensure your firewall allows port 8000.

### Offline Demo Mode

When no backend is reachable, the app automatically enters **Offline Demo Mode**:

- Badge shows: 🟠 **OFFLINE DEMO**
- All 4 demo scenarios work completely client-side:
  - ✅ Confirmed Flood
  - ❌ False Alarm
  - 📡 Missing Telemetry
  - 🚨 Multi-Crisis / Contradiction
- Animated agent traces appear in the terminal
- Scorecards update with scenario-appropriate metrics
- Map markers appear (if Google Maps API is available)
- Result overlay shows incident details
- Alert notifications prepend to the alerts list

---

## PWA Fallback

If APK build is not possible, CIRO works as a Progressive Web App:

1. Start the backend: `uvicorn main:app --host 0.0.0.0 --port 8000`
2. Open `http://localhost:8000/static/index.html` in Chrome on mobile.
3. Chrome menu → **Add to Home Screen**.
4. The app icon will appear on the home screen.

---

## Troubleshooting

| Issue | Solution |
|:---|:---|
| `npx cap` not found | Run `npm install` first |
| Gradle sync fails | Open Android Studio, let it download SDK components |
| APK crashes on launch | Check that `webDir` in `capacitor.config.json` is `"static"` |
| App shows OFFLINE DEMO | Expected without backend — this is fully functional |
| 10.0.2.2 not reaching host | Ensure `uvicorn` is running with `--host 0.0.0.0` |
| Map not loading | Google Maps API key may be restricted by domain |

---

## Security Notes

- ✅ No API keys are bundled in the APK
- ✅ No `.env` or `firebase-credentials.json` in the APK
- ✅ The APK contains only static HTML/CSS/JS assets
- ✅ All backend communication uses HTTP/WS (configurable to HTTPS/WSS)
- ✅ `server.cleartext: true` in `capacitor.config.json` allows HTTP for local development

---

## Expected Output

| File | Location |
|:---|:---|
| Debug APK | `android/app/build/outputs/apk/debug/app-debug.apk` |
| Submission APK | Rename to `CIRO-Mobile-Demo.apk` |

---

*Built with CapacitorJS 6.x — CIRO AISeekho 2026*
