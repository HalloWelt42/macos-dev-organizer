"""SQLite-Datenbank mit FTS5 Volltextsuche."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from devradar.config import Config
from devradar.models import ProjectInfo, ProjectResponse, StatsResponse


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


class Database:
    def __init__(self, config: Config) -> None:
        self.db_path = config.db_path
        _ensure_dir(self.db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()
        if self.db_path.exists():
            os.chmod(str(self.db_path), 0o600)

    def _create_tables(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                project_type TEXT NOT NULL,
                description TEXT DEFAULT '',
                readme_content TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                last_modified TEXT DEFAULT '',
                detected_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS scan_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                projects_found INTEGER DEFAULT 0,
                projects_added INTEGER DEFAULT 0,
                projects_removed INTEGER DEFAULT 0
            );
        """)
        # readme_translated Spalte hinzufügen falls nicht vorhanden
        try:
            self.conn.execute("ALTER TABLE projects ADD COLUMN readme_translated TEXT DEFAULT ''")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # Spalte existiert bereits

        # FTS5 Tabelle separat, da IF NOT EXISTS anders funktioniert
        try:
            self.conn.execute("""
                CREATE VIRTUAL TABLE projects_fts USING fts5(
                    name, description, readme_content, tags,
                    content='projects', content_rowid='id'
                )
            """)
        except sqlite3.OperationalError:
            pass  # Tabelle existiert bereits
        self.conn.commit()

    def upsert_project(self, info: ProjectInfo) -> int:
        """Projekt einfügen oder aktualisieren. Gibt die ID zurück."""
        now = datetime.now(timezone.utc).isoformat()
        # Echtes Änderungsdatum: last_commit_date > now
        last_mod = info.metadata.get("last_commit_date", "") or now
        tags_json = json.dumps(info.tags, ensure_ascii=False)
        meta_json = json.dumps(info.metadata, ensure_ascii=False)

        cursor = self.conn.execute(
            "SELECT id FROM projects WHERE path = ?", (info.path,)
        )
        row = cursor.fetchone()

        if row:
            project_id = row["id"]
            self.conn.execute(
                """UPDATE projects SET
                    name = ?, project_type = ?, description = ?,
                    readme_content = ?, tags = ?, last_modified = ?,
                    metadata = ?
                WHERE id = ?""",
                (
                    info.name,
                    info.project_type,
                    info.description,
                    info.readme_content,
                    tags_json,
                    last_mod,
                    meta_json,
                    project_id,
                ),
            )
            # FTS aktualisieren
            self.conn.execute(
                "DELETE FROM projects_fts WHERE rowid = ?", (project_id,)
            )
        else:
            cursor = self.conn.execute(
                """INSERT INTO projects
                    (path, name, project_type, description, readme_content,
                     tags, last_modified, detected_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    info.path,
                    info.name,
                    info.project_type,
                    info.description,
                    info.readme_content,
                    tags_json,
                    last_mod,
                    info.metadata.get("first_commit_date", "") or now,
                    meta_json,
                ),
            )
            project_id = cursor.lastrowid

        # FTS eintrag
        self.conn.execute(
            """INSERT INTO projects_fts (rowid, name, description, readme_content, tags)
            VALUES (?, ?, ?, ?, ?)""",
            (project_id, info.name, info.description, info.readme_content, tags_json),
        )
        self.conn.commit()
        return project_id

    def remove_missing(self, existing_paths: set[str]) -> int:
        """Entferne Projekte deren Pfade nicht mehr existieren."""
        cursor = self.conn.execute("SELECT id, path FROM projects")
        to_remove = []
        for row in cursor.fetchall():
            if row["path"] not in existing_paths:
                to_remove.append(row["id"])

        for pid in to_remove:
            self.conn.execute("DELETE FROM projects_fts WHERE rowid = ?", (pid,))
            self.conn.execute("DELETE FROM projects WHERE id = ?", (pid,))

        if to_remove:
            self.conn.commit()
        return len(to_remove)

    def search(
        self,
        query: str = "",
        project_type: str = "",
        sort: str = "name",
    ) -> list[ProjectResponse]:
        """Projekte suchen und filtern."""
        if query:
            # FTS5 Suche
            sql = """
                SELECT p.* FROM projects p
                JOIN projects_fts f ON f.rowid = p.id
                WHERE projects_fts MATCH ?
            """
            params: list = [query + "*"]  # Prefix-Suche
            if project_type:
                sql += " AND p.project_type = ?"
                params.append(project_type)
        else:
            sql = "SELECT * FROM projects"
            params = []
            if project_type:
                sql += " WHERE project_type = ?"
                params.append(project_type)

        if sort == "modified":
            sql += " ORDER BY last_modified DESC"
        elif sort == "oldest":
            sql += " ORDER BY detected_at ASC"
        elif sort == "type":
            sql += " ORDER BY project_type, name"
        elif sort == "path":
            sql += " ORDER BY path COLLATE NOCASE"
        else:
            sql += " ORDER BY name COLLATE NOCASE"

        cursor = self.conn.execute(sql, params)
        return [self._row_to_response(row) for row in cursor.fetchall()]

    def get_project(self, project_id: int) -> ProjectResponse | None:
        cursor = self.conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        return self._row_to_response(row) if row else None

    def get_all_projects_compact(self) -> list[dict]:
        """Alle Projekte als kompakte Liste für LLM-Kontext."""
        cursor = self.conn.execute(
            "SELECT id, path, name, project_type, description, tags FROM projects ORDER BY name"
        )
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row["id"],
                "name": row["name"],
                "path": row["path"],
                "type": row["project_type"],
                "description": row["description"],
                "tags": json.loads(row["tags"]),
            })
        return results

    def get_stats(self) -> StatsResponse:
        cursor = self.conn.execute(
            "SELECT project_type, COUNT(*) as cnt FROM projects GROUP BY project_type"
        )
        by_type = {row["project_type"]: row["cnt"] for row in cursor.fetchall()}
        total = sum(by_type.values())

        cursor = self.conn.execute(
            "SELECT finished_at FROM scan_log ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        last_scan = row["finished_at"] if row else ""

        return StatsResponse(total=total, by_type=by_type, last_scan=last_scan)

    def log_scan(self, found: int, added: int, removed: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO scan_log (started_at, finished_at, projects_found,
               projects_added, projects_removed) VALUES (?, ?, ?, ?, ?)""",
            (now, now, found, added, removed),
        )
        self.conn.commit()

    def _row_to_response(self, row: sqlite3.Row) -> ProjectResponse:
        return ProjectResponse(
            id=row["id"],
            path=row["path"],
            name=row["name"],
            project_type=row["project_type"],
            description=row["description"],
            readme_content=row["readme_content"] or "",
            readme_translated=row["readme_translated"] if "readme_translated" in row.keys() else "",
            tags=json.loads(row["tags"]),
            last_modified=row["last_modified"],
            detected_at=row["detected_at"],
            metadata=json.loads(row["metadata"]),
        )

    def close(self) -> None:
        self.conn.close()
