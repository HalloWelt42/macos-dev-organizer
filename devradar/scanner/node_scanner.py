"""Scanner für Node.js-Projekte (package.json)."""

from __future__ import annotations

import json
from pathlib import Path

from devradar.models import ProjectInfo
from devradar.scanner.base import BaseScanner, register_scanner


@register_scanner
class NodeScanner(BaseScanner):
    def detect(self, path: Path) -> bool:
        pkg = path / "package.json"
        if not pkg.is_file():
            return False
        # Nicht node_modules/irgendwas/package.json
        return "node_modules" not in path.parts

    def scan(self, path: Path) -> ProjectInfo:
        pkg_path = path / "package.json"
        try:
            with open(pkg_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

        name = data.get("name", path.name)
        description = data.get("description", "")
        version = data.get("version", "")
        scripts = list(data.get("scripts", {}).keys())

        deps = data.get("dependencies", {})
        dev_deps = data.get("devDependencies", {})
        all_deps = {**deps, **dev_deps}

        tags = ["node"]
        if "svelte" in all_deps:
            tags.append("svelte")
        if "react" in all_deps:
            tags.append("react")
        if "vue" in all_deps:
            tags.append("vue")
        if "typescript" in all_deps:
            tags.append("typescript")
        if "tailwindcss" in all_deps or "@tailwindcss/vite" in all_deps:
            tags.append("tailwind")
        if "vite" in all_deps:
            tags.append("vite")
        if "express" in deps:
            tags.append("express")

        return ProjectInfo(
            path=str(path),
            name=name,
            project_type="node",
            description=description,
            tags=tags,
            metadata={
                "version": version,
                "scripts": scripts,
                "dep_count": len(deps),
                "dev_dep_count": len(dev_deps),
            },
        )
