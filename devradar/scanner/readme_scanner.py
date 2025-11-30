"""Scanner für README-Dateien (Volltextsuche)."""

from __future__ import annotations

from pathlib import Path

from devradar.models import ProjectInfo
from devradar.scanner.base import BaseScanner, register_scanner

MAX_README_LENGTH = 50000


@register_scanner
class ReadmeScanner(BaseScanner):
    def detect(self, path: Path) -> bool:
        for name in ("README.md", "README.txt", "README", "readme.md"):
            if (path / name).is_file():
                return True
        return False

    def scan(self, path: Path) -> ProjectInfo:
        content = ""
        for name in ("README.md", "README.txt", "README", "readme.md"):
            readme = path / name
            if readme.is_file():
                try:
                    text = readme.read_text(encoding="utf-8", errors="replace")
                    content = text[:MAX_README_LENGTH]
                except OSError:
                    pass
                break

        # Ersten sinnvollen Absatz als Beschreibung extrahieren
        # Überspringe Headings, Badges, leere Zeilen, Code-Blöcke
        description = ""
        in_code_block = False
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            if not stripped:
                continue
            # Headings, Badges, HTML, Trennlinien überspringen
            if stripped.startswith(("#", "=", "!", "<", "---", "***", "[![", "|")):
                continue
            # Zu kurze Zeilen (z.B. einzelne Wörter) überspringen
            if len(stripped) < 15:
                continue
            description = stripped[:200]
            break

        return ProjectInfo(
            path=str(path),
            name=path.name,
            project_type="readme",
            description=description,
            readme_content=content,
            tags=[],
        )
