"""Scanner für Docker-Projekte."""

from __future__ import annotations

from pathlib import Path

from devradar.models import ProjectInfo
from devradar.scanner.base import BaseScanner, register_scanner


@register_scanner
class DockerScanner(BaseScanner):
    def detect(self, path: Path) -> bool:
        return (
            (path / "docker-compose.yml").is_file()
            or (path / "docker-compose.yaml").is_file()
            or (path / "compose.yml").is_file()
            or (path / "compose.yaml").is_file()
            or (path / "Dockerfile").is_file()
        )

    def scan(self, path: Path) -> ProjectInfo:
        tags = ["docker"]
        services: list[str] = []
        compose_file = None

        for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
            candidate = path / name
            if candidate.is_file():
                compose_file = candidate
                tags.append("compose")
                break

        if (path / "Dockerfile").is_file():
            tags.append("dockerfile")

        # Einfaches Parsen der Services aus compose-Datei
        if compose_file:
            try:
                with open(compose_file, encoding="utf-8") as f:
                    in_services = False
                    for line in f:
                        stripped = line.rstrip()
                        if stripped == "services:":
                            in_services = True
                            continue
                        if in_services:
                            if stripped and not stripped.startswith(" ") and not stripped.startswith("\t"):
                                break
                            # Service-Name: eingerückt mit 2 Spaces, endet mit :
                            if stripped.startswith("  ") and not stripped.startswith("    "):
                                svc = stripped.strip().rstrip(":")
                                if svc:
                                    services.append(svc)
            except OSError:
                pass

        return ProjectInfo(
            path=str(path),
            name=path.name,
            project_type="docker",
            description=f"Docker-Projekt mit {len(services)} Services" if services else "Docker-Projekt",
            tags=tags,
            metadata={
                "services": services,
            },
        )
