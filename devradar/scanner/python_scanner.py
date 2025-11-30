"""Scanner für Python-Projekte."""

from __future__ import annotations

import tomllib
from pathlib import Path

from devradar.models import ProjectInfo
from devradar.scanner.base import BaseScanner, register_scanner


@register_scanner
class PythonScanner(BaseScanner):
    def detect(self, path: Path) -> bool:
        return (
            (path / "pyproject.toml").is_file()
            or (path / "setup.py").is_file()
            or (path / "requirements.txt").is_file()
        )

    def scan(self, path: Path) -> ProjectInfo:
        name = path.name
        description = ""
        tags = ["python"]
        deps: list[str] = []

        # pyproject.toml hat Priorität
        pyproject = path / "pyproject.toml"
        if pyproject.is_file():
            try:
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                project = data.get("project", {})
                name = project.get("name", name)
                description = project.get("description", "")
                deps = project.get("dependencies", [])
            except Exception:
                pass

        # requirements.txt als Fallback
        req_file = path / "requirements.txt"
        if req_file.is_file() and not deps:
            try:
                with open(req_file, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and not line.startswith("-"):
                            pkg = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
                            deps.append(pkg)
            except OSError:
                pass

        dep_names = [d.split(">=")[0].split("==")[0].split("[")[0].strip().lower() for d in deps]
        if "fastapi" in dep_names:
            tags.append("fastapi")
        if "flask" in dep_names:
            tags.append("flask")
        if "django" in dep_names:
            tags.append("django")

        return ProjectInfo(
            path=str(path),
            name=name,
            project_type="python",
            description=description,
            tags=tags,
            metadata={
                "dep_count": len(deps),
            },
        )
