"""
SQLite storage layer with FTS5 full-text search for evidence chunks.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

from .schema import EvidenceChunk


class EvidenceStore:
    """
    Persistent storage for evidence chunks using SQLite + FTS5.

    Provides:
    - Efficient storage and retrieval of evidence chunks
    - Full-text search via FTS5 (prepared for M3b)
    - De-duplication via evidence_id primary key
    - Stats and analytics

    Example:
        >>> store = EvidenceStore("index.sqlite")
        >>> store.upsert_chunks([chunk1, chunk2])
        2
        >>> stats = store.stats()
        >>> stats["rows"]
        2
    """

    def __init__(self, db_path: str | Path = "index.sqlite"):
        """
        Initialize evidence store.

        Args:
            db_path: Path to SQLite database (created if doesn't exist)
        """
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    @contextmanager
    def _conn(self):
        """Context manager for database connections."""
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def _init_schema(self):
        """Initialize database schema with FTS5 triggers."""
        with self._conn() as con:
            con.executescript("""
                PRAGMA journal_mode=WAL;

                -- Main evidence table
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    repo TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    author TEXT NOT NULL,
                    path TEXT NOT NULL,
                    start INTEGER NOT NULL,
                    end INTEGER NOT NULL,
                    lang TEXT,
                    text TEXT NOT NULL,
                    ownership REAL NOT NULL,
                    recency REAL NOT NULL,
                    quality REAL NOT NULL,
                    anchor TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_repo_commit ON evidence(repo, commit_sha);
                CREATE INDEX IF NOT EXISTS idx_path ON evidence(path);
                CREATE INDEX IF NOT EXISTS idx_quality ON evidence(quality);
                CREATE INDEX IF NOT EXISTS idx_recency ON evidence(recency);

                -- FTS5 virtual table for full-text search (M3b ready)
                CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(
                    text,
                    evidence_id UNINDEXED,
                    content='evidence',
                    content_rowid='rowid'
                );

                -- Triggers to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS evidence_ai AFTER INSERT ON evidence BEGIN
                    INSERT INTO evidence_fts(rowid, text, evidence_id)
                    VALUES (new.rowid, new.text, new.evidence_id);
                END;

                CREATE TRIGGER IF NOT EXISTS evidence_ad AFTER DELETE ON evidence BEGIN
                    INSERT INTO evidence_fts(evidence_fts, rowid, text, evidence_id)
                    VALUES('delete', old.rowid, old.text, old.evidence_id);
                END;

                CREATE TRIGGER IF NOT EXISTS evidence_au AFTER UPDATE ON evidence BEGIN
                    INSERT INTO evidence_fts(evidence_fts, rowid, text, evidence_id)
                    VALUES('delete', old.rowid, old.text, old.evidence_id);
                    INSERT INTO evidence_fts(rowid, text, evidence_id)
                    VALUES (new.rowid, new.text, new.evidence_id);
                END;
            """)

    def upsert_chunks(self, chunks: Iterable[EvidenceChunk]) -> int:
        """
        Insert or replace evidence chunks.

        Args:
            chunks: Iterable of EvidenceChunk instances

        Returns:
            Number of chunks written

        Example:
            >>> store.upsert_chunks([chunk1, chunk2])
            2
        """
        with self._conn() as con:
            cur = con.cursor()
            n = 0
            for c in chunks:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO evidence
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        c.evidence_id,
                        c.repo,
                        c.owner,
                        c.commit,
                        c.author,
                        c.path,
                        c.start,
                        c.end,
                        c.lang,
                        c.text,
                        c.ownership,
                        c.recency,
                        c.quality,
                        c.anchor,
                        c.created_at.isoformat(),
                    ),
                )
                n += 1
            return n

    def get_chunk(self, evidence_id: str) -> EvidenceChunk | None:
        """
        Retrieve a single chunk by ID.

        Args:
            evidence_id: Unique chunk identifier

        Returns:
            EvidenceChunk or None if not found
        """
        with self._conn() as con:
            cur = con.execute(
                "SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_chunk(row)

    def get_chunks_by_ids(self, evidence_ids: list[str]) -> list[EvidenceChunk]:
        """
        Retrieve multiple chunks by IDs.

        Args:
            evidence_ids: List of chunk identifiers

        Returns:
            List of EvidenceChunk objects

        Example:
            >>> chunks = store.get_chunks_by_ids(["id1", "id2"])
        """
        if not evidence_ids:
            return []

        with self._conn() as con:
            placeholders = ",".join("?" * len(evidence_ids))
            query = f"SELECT * FROM evidence WHERE evidence_id IN ({placeholders})"  # nosec B608
            cur = con.execute(query, evidence_ids)
            return [self._row_to_chunk(row) for row in cur.fetchall()]

    def iter_chunks(
        self,
        *,
        repo: str | None = None,
        min_quality: float | None = None,
        limit: int | None = None,
    ) -> Iterator[EvidenceChunk]:
        """
        Iterate over stored chunks with optional filters.

        Args:
            repo: Filter by repository name
            min_quality: Minimum quality threshold
            limit: Maximum number of chunks to return

        Yields:
            EvidenceChunk instances

        Example:
            >>> for chunk in store.iter_chunks(min_quality=1.0, limit=10):
            ...     print(chunk.anchor)
        """
        query = "SELECT * FROM evidence WHERE 1=1"
        params = []

        if repo:
            query += " AND repo = ?"
            params.append(repo)

        if min_quality is not None:
            query += " AND quality >= ?"
            params.append(min_quality)

        query += " ORDER BY quality DESC, recency DESC"

        if limit:
            query += f" LIMIT {limit}"

        with self._conn() as con:
            cur = con.execute(query, params)
            for row in cur:
                yield self._row_to_chunk(row)

    def stats(self) -> dict:
        """
        Get database statistics.

        Returns:
            Dictionary with stats:
            - rows: Total number of chunks
            - avg_quality: Average quality score
            - avg_recency: Average recency score
            - repos: Number of unique repositories
            - languages: Number of unique languages

        Example:
            >>> store.stats()
            {'rows': 642, 'avg_quality': 1.07, 'avg_recency': 0.83, ...}
        """
        with self._conn() as con:
            # Total rows
            (rows,) = con.execute("SELECT COUNT(*) FROM evidence").fetchone()

            # Average quality
            (avg_quality,) = con.execute(
                "SELECT COALESCE(AVG(quality), 0) FROM evidence"
            ).fetchone()

            # Average recency
            (avg_recency,) = con.execute(
                "SELECT COALESCE(AVG(recency), 0) FROM evidence"
            ).fetchone()

            # Unique repos
            (repos,) = con.execute(
                "SELECT COUNT(DISTINCT repo) FROM evidence"
            ).fetchone()

            # Unique languages
            (langs,) = con.execute(
                "SELECT COUNT(DISTINCT lang) FROM evidence WHERE lang IS NOT NULL"
            ).fetchone()

            return {
                "rows": rows,
                "avg_quality": round(avg_quality or 0, 3),
                "avg_recency": round(avg_recency or 0, 3),
                "repos": repos,
                "languages": langs,
            }

    def clear(self):
        """
        Clear all evidence from the database.

        Warning: This is destructive!
        """
        with self._conn() as con:
            con.execute("DELETE FROM evidence")

    @staticmethod
    def _row_to_chunk(row: sqlite3.Row) -> EvidenceChunk:
        """Convert database row to EvidenceChunk."""
        from datetime import datetime

        return EvidenceChunk(
            evidence_id=row["evidence_id"],
            repo=row["repo"],
            owner=row["owner"],
            commit=row["commit_sha"],
            author=row["author"],
            path=row["path"],
            start=row["start"],
            end=row["end"],
            text=row["text"],
            lang=row["lang"],
            ownership=row["ownership"],
            recency=row["recency"],
            quality=row["quality"],
            anchor=row["anchor"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )