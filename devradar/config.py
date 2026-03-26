"""Konfiguration für DevRadar."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "devradar" / "config.toml"
DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "devradar" / "index.db"
DEFAULT_PORT = 10700

DEFAULT_SCAN_ROOTS: list[Path] = []

DEFAULT_IGNORE = [
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".nuxt",
]

# macOS TCC-geschützte Ordner -- Zugriff löst Systemdialoge aus
MACOS_PROTECTED_DIRS = {
    "Library",
    "Applications",
    "Pictures",
    "Movies",
    "Music",
    "Public",
    "Desktop",
    "Documents",
    "Downloads",
    ".Trash",
}


@dataclass
class LLMConfig:
    enabled: bool = False
    base_url: str = "http://localhost:1234/v1"
    model: str = "qwen3-next-80b-a3b-instruct-mlx"
    timeout: int = 14400


@dataclass
class Config:
    port: int = DEFAULT_PORT
    db_path: Path = DEFAULT_DB_PATH
    scan_roots: list[Path] = field(default_factory=lambda: list(DEFAULT_SCAN_ROOTS))
    max_depth: int = 4
    ignore_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE))
    ide_type: str = "jetbrains"
    llm: LLMConfig = field(default_factory=LLMConfig)
    rescan_interval_minutes: int = 30

    def save(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        """Speichere Konfiguration als TOML-Datei."""
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "[server]",
            f"port = {self.port}",
            "",
            "[scanner]",
            "roots = [",
        ]
        for root in self.scan_roots:
            lines.append(f'    "{root}",')
        lines.append("]")
        lines.append(f"max_depth = {self.max_depth}")
        ignore_list = ", ".join(f'"{p}"' for p in self.ignore_patterns)
        lines.append(f"ignore = [{ignore_list}]")
        lines.append("")
        lines.append("[ide]")
        lines.append(f'type = "{self.ide_type}"')
        lines.append("")
        lines.append("[llm]")
        lines.append(f"enabled = {'true' if self.llm.enabled else 'false'}")
        lines.append(f'base_url = "{self.llm.base_url}"')
        lines.append(f'model = "{self.llm.model}"')
        lines.append(f"timeout = {self.llm.timeout}")
        lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> Config:
        """Lade Konfiguration aus TOML-Datei. Nutze Defaults wenn Datei fehlt."""
        config = cls()
        if not path.exists():
            return config

        with open(path, "rb") as f:
            data = tomllib.load(f)

        server = data.get("server", {})
        if "port" in server:
            config.port = server["port"]

        scanner = data.get("scanner", {})
        if "roots" in scanner:
            config.scan_roots = [Path(r) for r in scanner["roots"]]
        if "max_depth" in scanner:
            config.max_depth = scanner["max_depth"]
        if "ignore" in scanner:
            config.ignore_patterns = scanner["ignore"]

        ide = data.get("ide", {})
        if "type" in ide:
            config.ide_type = ide["type"]

        llm = data.get("llm", {})
        if llm:
            config.llm = LLMConfig(
                enabled=llm.get("enabled", True),
                base_url=llm.get("base_url", config.llm.base_url),
                model=llm.get("model", config.llm.model),
                timeout=llm.get("timeout", config.llm.timeout),
            )

        return config
