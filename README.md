# DevRadar

Lokales Projekt-Dashboard für macOS. DevRadar scannt konfigurierbare Verzeichnisse nach Softwareprojekten, indiziert sie und stellt ein Web-Dashboard bereit.

![DevRadar](docs/screenshot.png)

## Features

- **Projektscanner** -- Erkennt automatisch Git-Repositories, Node.js-, Python-, Docker- und Browser-Extension-Projekte
- **Volltextsuche** -- Schnelle FTS5-basierte Suche über Projektnamen, Beschreibungen, READMEs und Tags
- **KI-Integration** -- Optionale Anbindung an lokale LLMs für intelligente Projektsuche und automatische Beschreibungen
- **README-Viewer** -- Integrierte Anzeige mit Syntax-Highlighting, Zoom und Übersetzung ins Deutsche
- **Mehrere Ansichten** -- Karten- und Listenansicht mit flexibler Filterung und Sortierung
- **Dateisystem-Überwachung** -- Automatischer Rescan bei Änderungen in den Projektverzeichnissen
- **macOS-Integration** -- Projekte direkt im Finder, Terminal oder der IDE öffnen
- **Erststart-Assistent** -- Führt beim ersten Start durch die Konfiguration der Scan-Verzeichnisse

## Installation

```bash
git clone https://github.com/HalloWelt42/macos-dev-organizer.git
cd macos-dev-organizer
./support/install.sh
```

Das Script erstellt eine Python-Umgebung, baut das Frontend und richtet einen macOS-LaunchAgent ein, der DevRadar automatisch startet.

Nach der Installation ist das Dashboard unter [http://localhost:10700](http://localhost:10700) erreichbar.

## Erststart

Beim ersten Start müssen Scan-Verzeichnisse konfiguriert werden. Das Dashboard zeigt einen Willkommens-Dialog, der durch die Einrichtung führt. Über den Button "Pfade" können jederzeit weitere Verzeichnisse hinzugefügt oder entfernt werden.

## KI-Integration (optional)

DevRadar kann optional ein lokales LLM nutzen (z.B. über LM Studio). Die KI-Funktionen umfassen:

- Natürlichsprachliche Projektsuche
- Automatische Projektbeschreibungen generieren
- README-Übersetzung ins Deutsche

Die KI-Einstellungen sind über die Sidebar konfigurierbar und standardmäßig deaktiviert.

## Technologie

| Komponente | Technologie |
|---|---|
| Backend | Python, FastAPI, SQLite (FTS5) |
| Frontend | Svelte 5, TypeScript, Tailwind CSS |
| Icons | FontAwesome 7 |
| Build | Vite |
| Markdown | marked.js, highlight.js |
| Prozessmanagement | macOS LaunchAgent |

## Projektstruktur

```
devradar/          Python-Backend (FastAPI, Scanner, Datenbank)
frontend/          Svelte 5 SPA (Dashboard, Detailansicht)
support/           Installationsskripte und LaunchAgent-Template
docs/              Screenshots
```

## Lizenz

MIT
