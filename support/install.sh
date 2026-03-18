#!/bin/bash
set -e

# Projektverzeichnis relativ zum Script ermitteln
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$HOME/.local/share/devradar"
PLIST_DST="$HOME/Library/LaunchAgents/de.alpha.devradar.plist"

echo "=== DevRadar Installation ==="

# Datenverzeichnis anlegen
mkdir -p "$DATA_DIR"
echo "Datenverzeichnis: $DATA_DIR"

# Python venv
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Erstelle Python venv..."
    python3 -m venv "$PROJECT_DIR/.venv"
fi

echo "Installiere Python-Abhängigkeiten..."
"$PROJECT_DIR/.venv/bin/pip" install -q -e "$PROJECT_DIR"

# Frontend
echo "Installiere Frontend-Abhängigkeiten..."
cd "$PROJECT_DIR/frontend"
npm install --silent

echo "Baue Frontend..."
npm run build

# LaunchAgent-Plist dynamisch generieren
echo "Generiere LaunchAgent..."
cat > "$PLIST_DST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>de.alpha.devradar</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PROJECT_DIR}/.venv/bin/python</string>
        <string>-m</string>
        <string>devradar.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${HOME}/.local/share/devradar/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${HOME}/.local/share/devradar/stderr.log</string>
</dict>
</plist>
PLIST

# LaunchAgent installieren
echo "Installiere LaunchAgent..."
launchctl bootout gui/$(id -u) "$PLIST_DST" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$PLIST_DST"

echo ""
echo "=== Installation abgeschlossen ==="
echo "DevRadar läuft auf: http://localhost:10700"
echo "Öffne im Browser..."
open "http://localhost:10700"
