"""Scanner für Git-Repositories."""

from __future__ import annotations

import subprocess
from pathlib import Path

from devradar.models import ProjectInfo
from devradar.scanner.base import BaseScanner, register_scanner


@register_scanner
class GitScanner(BaseScanner):
    def detect(self, path: Path) -> bool:
        return (path / ".git").is_dir()

    def scan(self, path: Path) -> ProjectInfo:
        name = path.name
        remote_url = ""
        branch = ""
        last_commit = ""

        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                remote_url = result.stdout.strip()
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%s", "--date=short"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                last_commit = result.stdout.strip()
        except Exception:
            pass

        # Letzter Commit-Zeitpunkt (ISO)
        last_commit_date = ""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%aI"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                last_commit_date = result.stdout.strip()
        except Exception:
            pass

        # Erster Commit-Zeitpunkt (Projektalter)
        first_commit_date = ""
        try:
            result = subprocess.run(
                ["git", "log", "--reverse", "--format=%aI", "--max-count=1"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                first_commit_date = result.stdout.strip()
        except Exception:
            pass

        tags = ["git"]
        if remote_url:
            if "github.com" in remote_url:
                tags.append("github")
            elif "gitlab" in remote_url:
                tags.append("gitlab")

        return ProjectInfo(
            path=str(path),
            name=name,
            project_type="git",
            description=last_commit,
            tags=tags,
            metadata={
                "remote_url": remote_url,
                "branch": branch,
                "last_commit": last_commit,
                "last_commit_date": last_commit_date,
                "first_commit_date": first_commit_date,
            },
        )
