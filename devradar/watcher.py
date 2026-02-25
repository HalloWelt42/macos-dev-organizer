"""Dateisystem-Überwachung mit watchdog (FSEvents auf macOS)."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from devradar.config import Config

logger = logging.getLogger(__name__)

# Dateien die auf ein neues Projekt hindeuten
MARKER_FILES = {
    "package.json",
    "manifest.json",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "Dockerfile",
    "pyproject.toml",
    "setup.py",
    "requirements.txt",
    ".git",
}


class ProjectChangeHandler(FileSystemEventHandler):
    """Handler der Änderungen sammelt und nach Debounce weitergibt."""

    def __init__(self, callback: callable, debounce_seconds: float = 5.0) -> None:
        self.callback = callback
        self.debounce = debounce_seconds
        self._changed_paths: set[str] = set()
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            name = Path(event.src_path).name
            if name in MARKER_FILES:
                self._handle(event)

    def _handle(self, event: FileSystemEvent) -> None:
        path = Path(event.src_path)
        # Projekt-Verzeichnis bestimmen (Elternverzeichnis der Marker-Datei)
        if path.is_file() or not path.exists():
            project_dir = str(path.parent)
        else:
            project_dir = str(path)

        with self._lock:
            self._changed_paths.add(project_dir)
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            paths = self._changed_paths.copy()
            self._changed_paths.clear()
        if paths:
            logger.info("Änderungen erkannt in %d Verzeichnissen, starte Rescan", len(paths))
            self.callback(paths)


class FileWatcher:
    """Überwacht konfigurierte Verzeichnisse auf Änderungen."""

    def __init__(self, config: Config, on_change: callable) -> None:
        self.config = config
        self.handler = ProjectChangeHandler(on_change)
        self.observer = Observer()

    def start(self) -> None:
        for root in self.config.scan_roots:
            if root.exists():
                self.observer.schedule(self.handler, str(root), recursive=True)
                logger.info("Überwache: %s", root)
        self.observer.daemon = True
        self.observer.start()

    def stop(self) -> None:
        self.observer.stop()
        self.observer.join(timeout=5)
