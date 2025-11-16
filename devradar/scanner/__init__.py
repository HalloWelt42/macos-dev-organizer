"""Scanner-Module für die automatische Projekterkennung."""

from devradar.scanner.base import BaseScanner, scanner_registry, run_all_scanners
from devradar.scanner.git_scanner import GitScanner
from devradar.scanner.node_scanner import NodeScanner
from devradar.scanner.extension_scanner import ExtensionScanner
from devradar.scanner.docker_scanner import DockerScanner
from devradar.scanner.python_scanner import PythonScanner
from devradar.scanner.readme_scanner import ReadmeScanner

__all__ = [
    "BaseScanner",
    "scanner_registry",
    "run_all_scanners",
    "GitScanner",
    "NodeScanner",
    "ExtensionScanner",
    "DockerScanner",
    "PythonScanner",
    "ReadmeScanner",
]
