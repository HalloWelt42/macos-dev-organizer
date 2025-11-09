"""Pydantic-Modelle für DevRadar."""

from __future__ import annotations

from pydantic import BaseModel


class ProjectInfo(BaseModel):
    """Ergebnis eines Scanners für ein Projekt."""

    path: str
    name: str
    project_type: str  # git, node, extension, docker, python
    description: str = ""
    readme_content: str = ""
    tags: list[str] = []
    metadata: dict = {}


class ProjectResponse(BaseModel):
    """Projekt-Antwort für die API."""

    id: int
    path: str
    name: str
    project_type: str
    description: str = ""
    readme_content: str = ""
    readme_translated: str = ""
    tags: list[str] = []
    last_modified: str = ""
    detected_at: str = ""
    metadata: dict = {}


class OpenRequest(BaseModel):
    """Anfrage zum Öffnen eines Projekts."""

    path: str
    app: str = "finder"  # finder, terminal, ide


class AskRequest(BaseModel):
    """Anfrage für die LLM-Suche."""

    question: str


class AskResponse(BaseModel):
    """Antwort der LLM-Suche."""

    answer: str
    project_ids: list[int] = []
    fallback: bool = False


class StatsResponse(BaseModel):
    """Statistiken über alle Projekte."""

    total: int = 0
    by_type: dict[str, int] = {}
    last_scan: str = ""
