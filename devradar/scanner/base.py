"""Basis-Scanner und Registry für die automatische Projekterkennung."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from devradar.config import MACOS_PROTECTED_DIRS, Config
from devradar.models import ProjectInfo

logger = logging.getLogger(__name__)

scanner_registry: list[type[BaseScanner]] = []


def register_scanner(cls: type[BaseScanner]) -> type[BaseScanner]:
    """Decorator um einen Scanner in der Registry zu registrieren."""
    scanner_registry.append(cls)
    return cls


class BaseScanner(ABC):
    """Abstrakte Basisklasse für Projekt-Scanner."""

    @abstractmethod
    def detect(self, path: Path) -> bool:
        """Prüft ob der Scanner dieses Verzeichnis erkennt."""
        ...

    @abstractmethod
    def scan(self, path: Path) -> ProjectInfo:
        """Scannt das Verzeichnis und gibt Projektinfos zurück."""
        ...


def scan_directory(path: Path, config: Config) -> list[ProjectInfo]:
    """Scannt ein einzelnes Verzeichnis mit allen registrierten Scannern."""
    results: list[ProjectInfo] = []
    scanners = [cls() for cls in scanner_registry]

    for scanner in scanners:
        try:
            if scanner.detect(path):
                info = scanner.scan(path)
                results.append(info)
        except Exception as e:
            logger.warning("Scanner %s fehlgeschlagen bei %s: %s", type(scanner).__name__, path, e)

    return results


from typing import Callable

def run_all_scanners(config: Config, on_path: Callable[[str], None] | None = None) -> list[ProjectInfo]:
    """Durchlaufe alle konfigurierten Wurzelverzeichnisse und scanne Projekte."""
    all_results: list[ProjectInfo] = []
    seen_paths: set[str] = set()

    for root in config.scan_roots:
        if not root.exists():
            logger.info("Scan-Root existiert nicht: %s", root)
            continue
        _walk(root, config, 0, all_results, seen_paths, on_path)

    return all_results


def _walk(
    path: Path,
    config: Config,
    depth: int,
    results: list[ProjectInfo],
    seen: set[str],
    on_path: Callable[[str], None] | None = None,
) -> None:
    """Rekursives Durchlaufen mit Tiefenbegrenzung."""
    if depth > config.max_depth:
        return

    path_str = str(path)
    if path_str in seen:
        return

    if on_path:
        on_path(path_str)

    # Dieses Verzeichnis scannen
    found = scan_directory(path, config)
    if found:
        seen.add(path_str)
        # Haupttyp bestimmen: Bevorzuge spezifische Typen vor git/readme
        type_priority = ["node", "extension", "python", "docker", "git", "readme"]
        found.sort(key=lambda f: type_priority.index(f.project_type) if f.project_type in type_priority else 99)
        primary = found[0]

        all_tags = set(primary.tags)
        all_meta = dict(primary.metadata)

        # Beschreibungen nach Qualität sortiert sammeln
        descriptions: list[tuple[int, str]] = []
        # Priorität: 0=README, 1=package.json/manifest, 2=git-commit
        desc_priority = {"readme": 0, "extension": 1, "node": 1, "python": 1, "docker": 2, "git": 3}
        for info in found:
            if info.description:
                prio = desc_priority.get(info.project_type, 2)
                descriptions.append((prio, info.description))
            if info.readme_content and not primary.readme_content:
                primary.readme_content = info.readme_content

        for extra in found[1:]:
            all_tags.update(extra.tags)
            all_tags.add(extra.project_type)
            all_meta.update(extra.metadata)

        # Beste Beschreibung wählen (niedrigste Priorität = beste)
        if descriptions:
            descriptions.sort(key=lambda x: x[0])
            primary.description = descriptions[0][1]

        primary.tags = sorted(all_tags)
        primary.metadata = all_meta
        results.append(primary)

    # Unterverzeichnisse durchlaufen
    try:
        for child in sorted(path.iterdir()):
            name = child.name
            if name.startswith("."):
                continue
            if name in config.ignore_patterns:
                continue
            # macOS TCC-geschützte Ordner überspringen (vermeidet Systemdialoge)
            if name in MACOS_PROTECTED_DIRS:
                continue
            try:
                if not child.is_dir():
                    continue
            except PermissionError:
                continue
            _walk(child, config, depth + 1, results, seen, on_path)
    except PermissionError:
        pass
