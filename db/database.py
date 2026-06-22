"""SQLite access layer for the Safran R&D Knowledge Assistant."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from db.models import ChunkRecord, ProjectRecord

logger = logging.getLogger(__name__)


class Database:
    """Small sqlite3 wrapper with schema initialisation and parameterised helpers."""

    def __init__(self, db_path: Path, schema_path: Path | None = None) -> None:
        self.db_path = Path(db_path)
        self.schema_path = schema_path or Path(__file__).with_name("schema.sql")
        self.connection: sqlite3.Connection | None = None

    def __enter__(self) -> "Database":
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def connect(self) -> sqlite3.Connection:
        """Open a SQLite connection and enable WAL and foreign key enforcement."""

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL;")
        self.connection.execute("PRAGMA foreign_keys=ON;")
        return self.connection

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the active connection, opening it if needed."""

        if self.connection is None:
            return self.connect()
        return self.connection

    def close(self) -> None:
        """Close the current connection."""

        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def init_schema(self) -> None:
        """Create all database tables and indexes."""

        schema = self.schema_path.read_text(encoding="utf-8")
        self.conn.executescript(schema)
        self.conn.commit()

    def reset(self) -> None:
        """Drop data tables and recreate the schema."""

        self.conn.executescript(
            """
            DROP TABLE IF EXISTS keywords;
            DROP TABLE IF EXISTS chunks;
            DROP TABLE IF EXISTS projects;
            """
        )
        self.init_schema()

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute a parameterised statement."""

        cursor = self.conn.execute(query, params)
        self.conn.commit()
        return cursor

    def executemany(self, query: str, params: Iterable[tuple[Any, ...]]) -> None:
        """Execute a parameterised statement for many rows."""

        self.conn.executemany(query, params)
        self.conn.commit()

    def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        """Fetch one row from a parameterised query."""

        return self.conn.execute(query, params).fetchone()

    def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """Fetch all rows from a parameterised query."""

        return list(self.conn.execute(query, params).fetchall())

    def project_exists(self, filename: str, date_modified: str | None) -> bool:
        """Return True when a document with the same filename and modified date exists."""

        row = self.fetchone(
            "SELECT id FROM projects WHERE filename = ? AND COALESCE(date_modified, '') = COALESCE(?, '')",
            (filename, date_modified),
        )
        return row is not None

    def insert_project(
        self,
        filename: str,
        title: str,
        raw_text: str,
        author: str | None,
        date_created: str | None,
        date_modified: str | None,
        file_type: str,
        word_count: int,
        ingested_at: str,
    ) -> int:
        """Insert one project and return its generated id."""

        cursor = self.execute(
            """
            INSERT INTO projects
                (filename, title, raw_text, author, date_created, date_modified, file_type, word_count, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (filename, title, raw_text, author, date_created, date_modified, file_type, word_count, ingested_at),
        )
        return int(cursor.lastrowid)

    def insert_chunks(self, project_id: int, chunks: list[str]) -> list[int]:
        """Insert chunks for one project and return generated ids."""

        ids: list[int] = []
        for index, content in enumerate(chunks):
            cursor = self.execute(
                "INSERT INTO chunks (project_id, chunk_index, content, embedding) VALUES (?, ?, ?, NULL)",
                (project_id, index, content),
            )
            ids.append(int(cursor.lastrowid))
        return ids

    def insert_keywords(self, project_id: int, keywords: list[str]) -> None:
        """Insert keyword rows for one project."""

        self.executemany(
            "INSERT INTO keywords (project_id, keyword) VALUES (?, ?)",
            [(project_id, keyword) for keyword in keywords],
        )

    def get_all_chunks(self) -> list[ChunkRecord]:
        """Return every chunk ordered by id."""

        rows = self.fetchall("SELECT id, project_id, chunk_index, content FROM chunks ORDER BY id")
        return [ChunkRecord(int(r["id"]), int(r["project_id"]), int(r["chunk_index"]), str(r["content"])) for r in rows]

    def get_project(self, project_id: int) -> ProjectRecord | None:
        """Return one project by id."""

        row = self.fetchone("SELECT * FROM projects WHERE id = ?", (project_id,))
        if row is None:
            return None
        return ProjectRecord(
            id=int(row["id"]),
            filename=str(row["filename"]),
            title=str(row["title"] or ""),
            raw_text=str(row["raw_text"] or ""),
            author=row["author"],
            date_created=row["date_created"],
            date_modified=row["date_modified"],
            file_type=str(row["file_type"] or ""),
            word_count=int(row["word_count"] or 0),
            ingested_at=str(row["ingested_at"] or ""),
        )

    def stats(self) -> dict[str, Any]:
        """Return high-level database statistics for the UI."""

        projects = self.fetchone("SELECT COUNT(*) AS count FROM projects")
        chunks = self.fetchone("SELECT COUNT(*) AS count FROM chunks")
        last = self.fetchone("SELECT MAX(ingested_at) AS last_ingestion FROM projects")
        return {
            "projects": int(projects["count"] if projects else 0),
            "chunks": int(chunks["count"] if chunks else 0),
            "last_ingestion": last["last_ingestion"] if last else None,
        }
