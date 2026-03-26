# Datenschutz

DevRadar ist eine lokal betriebene Anwendung.

## Datenverarbeitung

- DevRadar speichert alle Daten ausschließlich lokal auf Ihrem Gerät
- Es werden keine personenbezogenen Daten an externe Server übermittelt
- Projektdaten werden in einer lokalen SQLite-Datenbank gespeichert

## Externe Dienste

DevRadar nutzt folgende externe Dienste ausschließlich auf Nutzeranfrage:

- **YouTube Thumbnails** - Werden über den lokalen Proxy geladen und gecacht (img.youtube.com)
- **Badge-Bilder** - Externe Bilder in READMEs (z.B. shields.io) werden über den lokalen Proxy geladen und gecacht
- **LLM-Server** - Optionale Anbindung an einen vom Nutzer konfigurierten, lokalen LLM-Server

Bei der Nutzung externer Dienste gelten deren jeweilige Datenschutzbestimmungen.

## Cookies und Tracking

DevRadar verwendet keine Cookies und kein Tracking.

## Lokale Speicherung

- Datenbankdatei: `~/.local/share/devradar/index.db` (Berechtigung: nur Eigentümer)
- Konfiguration: `~/.config/devradar/config.toml`
- Beide Dateien enthalten nur Projektmetadaten, keine personenbezogenen Daten
