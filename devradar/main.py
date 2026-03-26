"""FastAPI-Hauptanwendung für DevRadar."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from devradar.config import Config
from devradar.database import Database
from devradar.llm import ask_llm, is_available, stream_llm
from devradar.models import (
    AskRequest,
    AskResponse,
    OpenRequest,
    ProjectResponse,
    StatsResponse,
)
from devradar.opener import open_project
from devradar.scanner import run_all_scanners
from devradar.watcher import FileWatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

config = Config.load()
db: Database | None = None
watcher: FileWatcher | None = None
scanning_active = False


def do_scan() -> dict:
    """Führe einen kompletten Scan durch."""
    global scanning_active
    assert db is not None
    scanning_active = True
    results = run_all_scanners(config)
    existing_paths: set[str] = set()
    added = 0

    for info in results:
        if not scanning_active:
            logger.info("Scan abgebrochen")
            break
        existing_paths.add(info.path)
        db.upsert_project(info)
        added += 1

    removed = db.remove_missing(existing_paths) if scanning_active else 0
    db.log_scan(found=len(results), added=added, removed=removed)
    scanning_active = False
    logger.info("Scan abgeschlossen: %d Projekte gefunden, %d entfernt", len(results), removed)
    return {"found": len(results), "removed": removed}


def on_fs_change(changed_paths: set[str]) -> None:
    """Callback für Dateisystem-Änderungen."""
    logger.info("Dateisystem-Änderung, starte Rescan")
    do_scan()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, watcher

    # Startup
    db = Database(config)
    logger.info("Datenbank initialisiert: %s", config.db_path)

    # Initialer Scan
    do_scan()

    # Dateisystem-Watcher starten
    watcher = FileWatcher(config, on_fs_change)
    watcher.start()
    logger.info("Dateisystem-Überwachung gestartet")

    # Periodischer Rescan
    async def periodic_rescan():
        while True:
            await asyncio.sleep(config.rescan_interval_minutes * 60)
            do_scan()

    task = asyncio.create_task(periodic_rescan())

    yield

    # Shutdown
    task.cancel()
    if watcher:
        watcher.stop()
    if db:
        db.close()
    logger.info("DevRadar beendet")


from devradar import __version__

app = FastAPI(title="DevRadar", version=__version__, lifespan=lifespan)

# CORS: Nur Same-Origin erlauben (localhost auf konfiguriertem Port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{config.port}", f"http://127.0.0.1:{config.port}"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-DevRadar-Token"],
    allow_credentials=False,
)


# --- CSRF-Token: Zufallswert pro Sitzung ---
import secrets
_csrf_token = secrets.token_urlsafe(32)


@app.get("/api/token")
def get_csrf_token():
    """Liefert den CSRF-Token für die aktuelle Sitzung."""
    return {"token": _csrf_token}


@app.middleware("http")
async def csrf_check(request: Request, call_next):
    """Prüft CSRF-Token für alle schreibenden Requests."""
    if request.method in ("POST", "PUT", "DELETE"):
        token = request.headers.get("X-DevRadar-Token", "")
        if not secrets.compare_digest(token, _csrf_token):
            return StreamingResponse(
                iter(['{"detail":"Ungültiger Token"}']),
                status_code=403,
                media_type="application/json",
            )
    return await call_next(request)


# --- API-Endpunkte ---


@app.get("/api/file")
async def api_file(project_path: str = Query(...), file_path: str = Query(...)):
    """Liefere eine Datei aus einem Projektverzeichnis (für README-Bilder etc.)."""
    from pathlib import Path as _Path

    # Null-Bytes verhindern
    if "\x00" in project_path or "\x00" in file_path:
        raise HTTPException(status_code=400, detail="Ungültiger Pfad")

    project = _Path(project_path).resolve()

    # Sicherheit: Pfad muss in Scan-Roots liegen
    allowed = False
    for root in config.scan_roots:
        try:
            project.relative_to(root.resolve())
            allowed = True
            break
        except ValueError:
            continue
    if not allowed:
        raise HTTPException(status_code=403, detail="Zugriff verweigert")

    # Normalisieren und Path-Traversal verhindern
    full_path = (project / file_path).resolve()
    try:
        full_path.relative_to(project)
    except ValueError:
        raise HTTPException(status_code=403, detail="Pfad ausserhalb des Projekts")

    # Symlinks prüfen -- Ziel muss ebenfalls im Projekt liegen
    if full_path.is_symlink():
        real_target = full_path.resolve(strict=True)
        try:
            real_target.relative_to(project)
        except ValueError:
            raise HTTPException(status_code=403, detail="Symlink zeigt ausserhalb des Projekts")

    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")

    # Nur bekannte Dateitypen ausliefern
    ALLOWED_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
        ".mp4", ".webm", ".mov",
        ".md", ".txt", ".json", ".toml", ".yaml", ".yml",
        ".html", ".css", ".js", ".ts",
    }
    if full_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="Dateityp nicht erlaubt")

    # Cache-Header: Bilder/Videos lange cachen (Inhalt aendert sich selten)
    import hashlib
    stat = full_path.stat()
    etag = hashlib.md5(f"{full_path}:{stat.st_mtime}:{stat.st_size}".encode()).hexdigest()
    MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".mp4", ".webm"}
    if full_path.suffix.lower() in MEDIA_EXTENSIONS:
        cache_control = "public, max-age=86400, immutable"
    else:
        cache_control = "public, max-age=3600"

    return FileResponse(
        str(full_path),
        headers={"Cache-Control": cache_control, "ETag": f'"{etag}"'},
    )


import re as _re
import httpx as _httpx

# YouTube-Thumbnail Cache (im Speicher, max 200 Eintraege)
_yt_cache: dict[str, bytes] = {}
_YT_ID_RE = _re.compile(r"^[a-zA-Z0-9_-]{11}$")


@app.get("/api/yt-thumb/{video_id}")
async def youtube_thumbnail(video_id: str):
    """YouTube-Thumbnail als Proxy ausliefern (kein externer CDN-Aufruf vom Frontend)."""
    if not _YT_ID_RE.match(video_id):
        raise HTTPException(status_code=400, detail="Ungültige Video-ID")

    if video_id in _yt_cache:
        return StreamingResponse(
            iter([_yt_cache[video_id]]),
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=604800, immutable"},
        )

    # Thumbnail von YouTube laden
    url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    try:
        async with _httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail="Thumbnail nicht gefunden")
            data = resp.content
    except _httpx.RequestError:
        raise HTTPException(status_code=502, detail="YouTube nicht erreichbar")

    # Cache begrenzen
    if len(_yt_cache) > 200:
        oldest = next(iter(_yt_cache))
        del _yt_cache[oldest]
    _yt_cache[video_id] = data

    return StreamingResponse(
        iter([data]),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=604800, immutable"},
    )


# Bild-Proxy: Externe Bilder cachen und über eigenen Server ausliefern
_img_cache: dict[str, tuple[bytes, str]] = {}
# Bild-Proxy: Kein Host-Limit, aber nur Bild-Content-Types werden akzeptiert
_ALLOWED_IMG_CONTENT = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml", "image/x-icon"}


@app.get("/api/img-proxy")
async def image_proxy(url: str = Query(..., description="Externe Bild-URL")):
    """Externes Bild über den Server laden und gecacht ausliefern."""
    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Nur HTTP/HTTPS erlaubt")

    # Cache prüfen
    if url in _img_cache:
        data, ct = _img_cache[url]
        return StreamingResponse(
            iter([data]),
            media_type=ct,
            headers={"Cache-Control": "public, max-age=86400, immutable"},
        )

    try:
        async with _httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail="Bild nicht gefunden")
            ct = resp.headers.get("content-type", "").split(";")[0].strip()
            if ct not in _ALLOWED_IMG_CONTENT:
                raise HTTPException(status_code=403, detail=f"Kein erlaubter Bildtyp: {ct}")
            data = resp.content
    except _httpx.RequestError:
        raise HTTPException(status_code=502, detail="Bild nicht erreichbar")

    # Cache begrenzen (max 500 Einträge)
    if len(_img_cache) > 500:
        oldest = next(iter(_img_cache))
        del _img_cache[oldest]
    _img_cache[url] = (data, ct)

    return StreamingResponse(
        iter([data]),
        media_type=ct,
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )


@app.post("/api/projects/{project_id}/translate")
async def api_translate(project_id: int):
    """Übersetze die README eines Projekts ins Deutsche per LLM-Streaming."""
    assert db is not None
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    if not project.readme_content:
        raise HTTPException(status_code=400, detail="Keine README vorhanden")
    if not config.llm.enabled or not await is_available(config.llm):
        raise HTTPException(status_code=503, detail="LLM nicht verfügbar")

    translate_prompt = f"""Übersetze die folgende README-Datei ins Deutsche. Gib NUR die übersetzte README aus, KEINE Einleitung, KEINEN Kommentar, KEINE Erklärung.

ABSOLUTE REGELN:
1. Code-Blöcke (``` ... ```) KOMPLETT UNVERÄNDERT übernehmen.
2. Inline-Code (`...`) KOMPLETT UNVERÄNDERT übernehmen.
3. Markdown-Formatierung EXAKT beibehalten.
4. Fachbegriffe bleiben Englisch.
5. Produkt-/Projektnamen, URLs, Pfade, Dateinamen unverändert.
6. Badge-Links und Shield-URLs 1:1 übernehmen.
7. Natürlich klingend, nicht maschinell.
8. VOLLSTÄNDIG übersetzen, nichts weglassen.
9. KEINE Einleitung wie "Hier ist die Übersetzung" -- direkt mit dem Inhalt beginnen.

README:
{project.readme_content}"""

    async def translate_stream():
        projects_dummy = [{"id": project_id, "name": project.name}]
        full_text = ""
        async for chunk in stream_llm(translate_prompt, projects_dummy, config.llm):
            # Mitschneiden fuer Persistierung
            import json as _json
            try:
                line = chunk.strip()
                if line.startswith("data: "):
                    data = _json.loads(line[6:])
                    if data.get("type") == "done":
                        full_text = data.get("full", "")
                        # Persistieren
                        db.conn.execute(
                            "UPDATE projects SET readme_translated = ? WHERE id = ?",
                            (full_text, project_id),
                        )
                        db.conn.commit()
            except Exception:
                pass
            yield chunk

    return StreamingResponse(
        translate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.delete("/api/projects/{project_id}/translate")
async def api_delete_translation(project_id: int):
    """Lösche die Übersetzung eines Projekts."""
    assert db is not None
    db.conn.execute("UPDATE projects SET readme_translated = '' WHERE id = ?", (project_id,))
    db.conn.commit()
    return {"status": "ok"}


@app.get("/api/browse")
def browse_directory(path: str = Query("~", description="Verzeichnispfad")):
    """Verzeichnisse auf dem Server auflisten für den Ordner-Picker."""
    from pathlib import Path as _Path

    # Null-Bytes verhindern
    if "\x00" in path:
        raise HTTPException(status_code=400, detail="Ungültiger Pfad")

    target = _Path(path).expanduser().resolve()
    # Nur innerhalb des Home-Verzeichnisses browsen
    home = _Path.home().resolve()
    try:
        target.relative_to(home)
    except ValueError:
        raise HTTPException(status_code=403, detail="Zugriff nur innerhalb des Home-Verzeichnisses")
    if not target.is_dir():
        raise HTTPException(status_code=404, detail="Verzeichnis nicht gefunden")

    from devradar.config import MACOS_PROTECTED_DIRS
    dirs = []
    try:
        for child in sorted(target.iterdir()):
            name = child.name
            if name.startswith("."):
                continue
            if name in MACOS_PROTECTED_DIRS:
                continue
            try:
                if child.is_dir():
                    dirs.append({"name": name, "path": str(child)})
            except PermissionError:
                continue
    except PermissionError:
        pass

    return {
        "current": str(target),
        "parent": str(target.parent) if target != target.parent else None,
        "dirs": dirs[:100],
    }


@app.get("/api/llm/models")
async def get_llm_models():
    """Verfügbare Modelle vom LLM-Server abrufen."""
    if not config.llm.base_url:
        return {"models": []}
    import urllib.parse
    parsed = urllib.parse.urlparse(config.llm.base_url)
    if parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        return {"models": []}
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{config.llm.base_url}/models")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("id", "") for m in data.get("data", [])]
                return {"models": models}
    except Exception:
        pass
    return {"models": []}


@app.get("/api/config/roots")
def get_roots():
    """Aktuelle Scan-Wurzelverzeichnisse."""
    return {"roots": [str(r) for r in config.scan_roots]}


@app.post("/api/config/roots")
def set_roots(body: dict):
    """Scan-Wurzelverzeichnisse ändern und persistieren."""
    from pathlib import Path as _Path
    roots = body.get("roots", [])
    if not roots:
        raise HTTPException(status_code=400, detail="Mindestens ein Pfad erforderlich")
    config.scan_roots = [_Path(r) for r in roots if r.strip()]
    config.save()
    # Watcher neu starten
    if watcher:
        watcher.stop()
        watcher.__init__(config, on_fs_change)
        watcher.start()
    # Rescan
    do_scan()
    return {"status": "ok", "roots": [str(r) for r in config.scan_roots]}


@app.get("/api/config/llm")
def get_llm_config():
    """Aktuelle LLM-Konfiguration."""
    return {
        "enabled": config.llm.enabled,
        "base_url": config.llm.base_url,
        "model": config.llm.model,
    }


@app.post("/api/config/llm")
def set_llm_config(body: dict):
    """LLM-Konfiguration ändern und persistieren."""
    from devradar.config import LLMConfig
    config.llm = LLMConfig(
        enabled=body.get("enabled", config.llm.enabled),
        base_url=body.get("base_url", config.llm.base_url),
        model=body.get("model", config.llm.model),
    )
    config.save()
    return {
        "status": "ok",
        "enabled": config.llm.enabled,
        "base_url": config.llm.base_url,
        "model": config.llm.model,
    }


@app.get("/api/version")
def get_version():
    return {"version": __version__}


@app.get("/api/projects", response_model=list[ProjectResponse])
def get_projects(
    q: str = Query("", description="Suchbegriff"),
    type: str = Query("", description="Projekttyp-Filter"),
    sort: str = Query("name", description="Sortierung: name, modified, type"),
):
    assert db is not None
    return db.search(query=q, project_type=type, sort=sort)


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int):
    assert db is not None
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


@app.post("/api/open")
def api_open(request: OpenRequest):
    try:
        msg = open_project(request.path, request.app, config)
        return {"status": "ok", "message": msg}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rescan")
def api_rescan():
    result = do_scan()
    return {"status": "ok", **result}


@app.get("/api/rescan/stream")
async def api_rescan_stream():
    """SSE-Streaming-Rescan: Sendet den aktuellen Scan-Pfad als Event."""
    import asyncio
    import queue

    path_queue: queue.Queue[str | None] = queue.Queue()

    def on_path(p: str):
        path_queue.put(p)

    async def generate():
        import json
        import threading

        def run_scan():
            global scanning_active
            assert db is not None
            scanning_active = True
            results = run_all_scanners(config, on_path=on_path)
            existing_paths: set[str] = set()
            added = 0
            for info in results:
                if not scanning_active:
                    break
                existing_paths.add(info.path)
                db.upsert_project(info)
                added += 1
            removed = db.remove_missing(existing_paths) if scanning_active else 0
            db.log_scan(found=len(results), added=added, removed=removed)
            scanning_active = False
            path_queue.put(None)

        thread = threading.Thread(target=run_scan, daemon=True)
        thread.start()

        while True:
            try:
                p = path_queue.get(timeout=0.1)
                if p is None:
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    break
                yield f"data: {json.dumps({'type': 'path', 'path': p})}\n\n"
            except queue.Empty:
                await asyncio.sleep(0.05)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/scan/stop")
def stop_scan():
    global scanning_active
    scanning_active = False
    return {"status": "ok"}


@app.post("/api/ask")
async def api_ask(request: AskRequest):
    """Streaming-Endpunkt: Gibt SSE-Events mit Chunks und Stats zurück."""
    assert db is not None

    # Prüfe ob LLM verfügbar -> Streaming
    if config.llm.enabled and await is_available(config.llm):
        projects = db.get_all_projects_compact()
        return StreamingResponse(
            stream_llm(request.question, projects, config.llm),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Fallback: FTS5-Suche (nicht-streamend)
    results = db.search(query=request.question)
    names = [f"- {p.name} ({p.project_type})" for p in results[:10]]
    answer = f"LLM nicht verfügbar. FTS5-Suchergebnisse:\n" + "\n".join(names) if names else "Keine Ergebnisse gefunden."
    return AskResponse(
        answer=answer,
        project_ids=[p.id for p in results[:10]],
        fallback=True,
    )


@app.post("/api/projects/{project_id}/enrich")
async def api_enrich(project_id: int):
    """Lasse das LLM eine deutsche Beschreibung für ein Projekt generieren."""
    assert db is not None

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")

    if not config.llm.enabled or not await is_available(config.llm):
        raise HTTPException(status_code=503, detail="LLM nicht verfügbar")

    # Kontext zusammenbauen
    context_parts = [f"Projektname: {project.name}", f"Typ: {project.project_type}", f"Pfad: {project.path}"]
    if project.tags:
        context_parts.append(f"Tags: {', '.join(project.tags)}")
    if project.description:
        context_parts.append(f"Bisherige Beschreibung: {project.description}")
    if project.readme_content:
        context_parts.append(f"README (Auszug):\n{project.readme_content[:1500]}")
    if project.metadata:
        import json as _json
        context_parts.append(f"Metadaten: {_json.dumps(project.metadata, ensure_ascii=False)}")

    context = "\n".join(context_parts)

    from devradar.llm import stream_llm as _stream  # noqa: avoid circular

    enrich_prompt = f"""Erstelle eine knappe, informative Beschreibung auf Deutsch für folgendes Projekt.
Die Beschreibung soll 2-4 Sätze lang sein und den Zweck, die Technologien und den Einsatzzweck zusammenfassen.
Nutze Markdown für die Formatierung.

{context}"""

    # Streaming-Antwort
    async def enrich_stream():
        projects_dummy = [{"id": project_id, "name": project.name}]
        async for chunk in _stream(enrich_prompt, projects_dummy, config.llm):
            yield chunk

    return StreamingResponse(
        enrich_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/projects/{project_id}/description")
async def api_save_description(project_id: int, body: dict):
    """Speichere eine neue Beschreibung für ein Projekt."""
    assert db is not None
    description = body.get("description", "")
    if not description:
        raise HTTPException(status_code=400, detail="Beschreibung fehlt")

    db.conn.execute("UPDATE projects SET description = ? WHERE id = ?", (description, project_id))
    # FTS aktualisieren
    db.conn.execute("DELETE FROM projects_fts WHERE rowid = ?", (project_id,))
    row = db.conn.execute("SELECT name, description, readme_content, tags FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row:
        db.conn.execute(
            "INSERT INTO projects_fts (rowid, name, description, readme_content, tags) VALUES (?, ?, ?, ?, ?)",
            (project_id, row["name"], row["description"], row["readme_content"], row["tags"]),
        )
    db.conn.commit()
    return {"status": "ok"}


@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    assert db is not None
    return db.get_stats()


# --- Statische Dateien (Svelte-Build) ---

# Frontend dist/ Verzeichnis
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if _frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """SPA-Fallback: Alle nicht-API Routen liefern index.html."""
        # API-Pfade nicht abfangen
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API-Endpunkt nicht gefunden")
        file_path = _frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_dist / "index.html"))
else:
    @app.get("/")
    def serve_placeholder():
        return {"message": "DevRadar Backend läuft. Frontend noch nicht gebaut. Bitte `cd frontend && npm run build` ausführen."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=config.port)
