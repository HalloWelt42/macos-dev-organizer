"""macOS App-Öffnung für Projekte."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from devradar.config import Config

logger = logging.getLogger(__name__)

# JetBrains Toolbox CLI-Pfade
JETBRAINS_PATHS = {
    "webstorm": [
        "/usr/local/bin/webstorm",
        Path.home() / "Library/Application Support/JetBrains/Toolbox/scripts/webstorm",
    ],
    "pycharm": [
        "/usr/local/bin/pycharm",
        Path.home() / "Library/Application Support/JetBrains/Toolbox/scripts/pycharm",
    ],
    "phpstorm": [
        "/usr/local/bin/phpstorm",
        Path.home() / "Library/Application Support/JetBrains/Toolbox/scripts/phpstorm",
    ],
    "idea": [
        "/usr/local/bin/idea",
        Path.home() / "Library/Application Support/JetBrains/Toolbox/scripts/idea",
    ],
}

# Projekttyp -> bevorzugte IDE
TYPE_TO_IDE = {
    "node": "webstorm",
    "extension": "webstorm",
    "python": "pycharm",
    "docker": "webstorm",
}


def _find_jetbrains_cmd(ide_name: str) -> str | None:
    """Finde den CLI-Pfad für eine JetBrains IDE."""
    paths = JETBRAINS_PATHS.get(ide_name, [])
    for p in paths:
        p = Path(p)
        if p.exists():
            return str(p)
    return None


def _validate_path(path_str: str, config: Config) -> Path:
    """Prüfe ob der Pfad innerhalb der erlaubten Scan-Roots liegt."""
    path = Path(path_str).resolve()
    for root in config.scan_roots:
        try:
            path.relative_to(root.resolve())
            return path
        except ValueError:
            continue
    raise ValueError(f"Pfad liegt ausserhalb der erlaubten Verzeichnisse: {path}")


def open_project(path_str: str, app: str, config: Config) -> str:
    """Öffne ein Projekt in der angegebenen App.

    Args:
        path_str: Pfad zum Projekt
        app: "finder", "terminal" oder "ide"
        config: Konfiguration

    Returns:
        Statusmeldung
    """
    path = _validate_path(path_str, config)

    if not path.exists():
        raise FileNotFoundError(f"Pfad existiert nicht: {path}")

    if app == "finder":
        subprocess.run(["open", str(path)], check=True)
        return f"Finder geöffnet: {path}"

    if app == "terminal":
        subprocess.run(["open", "-a", "Terminal", str(path)], check=True)
        return f"Terminal geöffnet: {path}"

    if app == "ide":
        return _open_in_ide(path, config)

    raise ValueError(f"Unbekannte App: {app}")


def _open_in_ide(path: Path, config: Config) -> str:
    """Öffne Projekt in der passenden JetBrains IDE."""
    # Projekttyp erkennen
    ide_name = "webstorm"  # Default
    if (path / "pyproject.toml").exists() or (path / "requirements.txt").exists():
        ide_name = "pycharm"
    elif (path / "composer.json").exists():
        ide_name = "phpstorm"

    cmd = _find_jetbrains_cmd(ide_name)
    if cmd:
        subprocess.run([cmd, str(path)], check=True)
        return f"{ide_name} geöffnet: {path}"

    # Fallback: open -a
    app_names = {
        "webstorm": "WebStorm",
        "pycharm": "PyCharm Professional",
        "phpstorm": "PhpStorm",
    }
    app_name = app_names.get(ide_name, "WebStorm")
    try:
        subprocess.run(["open", "-a", app_name, str(path)], check=True)
        return f"{app_name} geöffnet: {path}"
    except subprocess.CalledProcessError:
        # Letzter Fallback: generisches open
        subprocess.run(["open", str(path)], check=True)
        return f"Finder geöffnet (IDE nicht gefunden): {path}"
