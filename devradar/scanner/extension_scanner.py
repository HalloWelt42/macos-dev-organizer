"""Scanner für Browser-Extensions (manifest.json mit manifest_version)."""

from __future__ import annotations

import json
from pathlib import Path

from devradar.models import ProjectInfo
from devradar.scanner.base import BaseScanner, register_scanner


def _resolve_i18n(value: str, path: Path) -> str:
    """Löse __MSG_xxx__ Platzhalter aus _locales/ auf."""
    if not value.startswith("__MSG_") or not value.endswith("__"):
        return value
    key = value[6:-2]  # z.B. "extName" aus "__MSG_extName__"
    # Versuche de, dann en als Fallback
    for lang in ("de", "en"):
        messages_file = path / "_locales" / lang / "messages.json"
        if messages_file.is_file():
            try:
                with open(messages_file, encoding="utf-8") as f:
                    messages = json.load(f)
                if key in messages:
                    return messages[key].get("message", value)
                # Case-insensitive Suche
                for k, v in messages.items():
                    if k.lower() == key.lower():
                        return v.get("message", value)
            except (json.JSONDecodeError, OSError):
                pass
    # Fallback: Verzeichnisname
    return path.name


@register_scanner
class ExtensionScanner(BaseScanner):
    def detect(self, path: Path) -> bool:
        manifest = path / "manifest.json"
        if not manifest.is_file():
            return False
        try:
            with open(manifest, encoding="utf-8") as f:
                data = json.load(f)
            return "manifest_version" in data
        except (json.JSONDecodeError, OSError):
            return False

    def scan(self, path: Path) -> ProjectInfo:
        manifest_path = path / "manifest.json"
        try:
            with open(manifest_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

        name = data.get("name", path.name)
        description = data.get("description", "")

        # i18n-Platzhalter auflösen (__MSG_xxx__)
        name = _resolve_i18n(name, path)
        description = _resolve_i18n(description, path)
        version = data.get("version", "")
        manifest_version = data.get("manifest_version", 0)
        permissions = data.get("permissions", [])

        tags = ["extension"]
        if manifest_version == 3:
            tags.append("mv3")
        elif manifest_version == 2:
            tags.append("mv2")

        # Browser-Typ erkennen
        if "browser_specific_settings" in data:
            if "gecko" in data["browser_specific_settings"]:
                tags.append("firefox")
        if "background" in data and "service_worker" in data.get("background", {}):
            tags.append("chrome")

        return ProjectInfo(
            path=str(path),
            name=name,
            project_type="extension",
            description=description,
            tags=tags,
            metadata={
                "version": version,
                "manifest_version": manifest_version,
                "permissions": permissions,
            },
        )
