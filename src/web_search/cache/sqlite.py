"""SQLite persistent cache implementation with TTL expiration and indexing."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

from web_search.cache.base import BaseCache
from web_search.exceptions import CacheError
from web_search.models import SearchResult


class SQLiteCache(BaseCache):
    """Persistent SQLite-backed cache for search queries with TTL and indexing."""

    def __init__(
        self,
        db_path: str | Path = "search_cache.db",
        default_ttl_seconds: int = 86400,  # 24 hours default for persistent cache
        auto_purge_interval: int = 3600,
    ):
        """Initialize SQLite cache.

        Args:
            db_path: Path to the SQLite database file or ':memory:'
            default_ttl_seconds: Cache TTL in seconds (default: 24 hours)
            auto_purge_interval: Periodic interval in seconds to purge expired entries
        """
        super().__init__(default_ttl_seconds=default_ttl_seconds)
        self.db_path = str(db_path)
        self.auto_purge_interval = auto_purge_interval
        self._last_purge = time.time()
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create or return existing configured SQLite connection."""
        if self._conn is None:
            if self.db_path != ":memory:":
                parent_dir = os.path.dirname(os.path.abspath(self.db_path))
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
            self._conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
            if self.db_path != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
        return self._conn

    def _init_db(self) -> None:
        """Initialize cache table and indexes."""
        if self.db_path != ":memory:":
            parent_dir = os.path.dirname(os.path.abspath(self.db_path))
            os.makedirs(parent_dir, exist_ok=True)

        try:
            with self._lock:
                with self._get_connection() as conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS search_cache (
                            cache_key TEXT PRIMARY KEY,
                            query TEXT NOT NULL,
                            results_json TEXT NOT NULL,
                            created_at REAL NOT NULL,
                            expires_at REAL NOT NULL
                        )
                    """)
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_search_cache_expires
                        ON search_cache (expires_at)
                    """)
                    conn.commit()
        except sqlite3.Error as e:
            raise CacheError(f"Failed to initialize SQLite cache database: {e}") from e

    def _maybe_auto_purge(self, conn: sqlite3.Connection) -> None:
        """Periodically purge expired entries."""
        now = time.time()
        if now - self._last_purge > self.auto_purge_interval:
            conn.execute("DELETE FROM search_cache WHERE expires_at < ?", (now,))
            self._last_purge = now

    def get(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
    ) -> Optional[list[SearchResult]]:
        """Retrieve cached results from SQLite if valid and not expired."""
        key = self.make_key(query, max_results, language, region)
        now = time.time()

        try:
            with self._lock:
                with self._get_connection() as conn:
                    self._maybe_auto_purge(conn)
                    cursor = conn.execute(
                        "SELECT results_json, expires_at FROM search_cache WHERE cache_key = ?",
                        (key,),
                    )
                    row = cursor.fetchone()
                    if not row:
                        return None

                    if now >= row["expires_at"]:
                        conn.execute(
                            "DELETE FROM search_cache WHERE cache_key = ?",
                            (key,),
                        )
                        conn.commit()
                        return None

                    raw_list = json.loads(row["results_json"])
                    return [
                        SearchResult(
                            titre=item["titre"],
                            url=item["url"],
                            extrait=item["extrait"],
                            engine=item.get("engine", "cached"),
                            rank=item.get("rank", idx + 1),
                            extra=item.get("extra", {}),
                        )
                        for idx, item in enumerate(raw_list)
                    ]
        except sqlite3.Error as e:
            raise CacheError(f"SQLite cache get error: {e}") from e

    def set(
        self,
        query: str,
        results: list[SearchResult],
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """Store results into SQLite cache."""
        key = self.make_key(query, max_results, language, region)
        ttl_seconds = ttl if ttl is not None else self.default_ttl_seconds
        now = time.time()
        expires_at = now + ttl_seconds

        serialized = json.dumps(
            [r.to_dict(include_metadata=True) for r in results],
            ensure_ascii=False,
        )

        try:
            with self._lock:
                with self._get_connection() as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO search_cache (cache_key, query, results_json, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (key, query, serialized, now, expires_at),
                    )
                    conn.commit()
        except sqlite3.Error as e:
            raise CacheError(f"SQLite cache set error: {e}") from e

    def delete(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
    ) -> bool:
        """Delete specific entry from SQLite cache."""
        key = self.make_key(query, max_results, language, region)
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "DELETE FROM search_cache WHERE cache_key = ?",
                        (key,),
                    )
                    conn.commit()
                    return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise CacheError(f"SQLite cache delete error: {e}") from e

    def clear(self) -> None:
        """Clear all entries in the cache table."""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    conn.execute("DELETE FROM search_cache")
                    conn.commit()
        except sqlite3.Error as e:
            raise CacheError(f"SQLite cache clear error: {e}") from e

    def purge_expired(self) -> int:
        """Purge all expired entries from SQLite."""
        now = time.time()
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "DELETE FROM search_cache WHERE expires_at < ?",
                        (now,),
                    )
                    conn.commit()
                    return cursor.rowcount
        except sqlite3.Error as e:
            raise CacheError(f"SQLite cache purge error: {e}") from e

    def size(self) -> int:
        """Return total active entries count."""
        now = time.time()
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM search_cache WHERE expires_at >= ?",
                        (now,),
                    )
                    row = cursor.fetchone()
                    return row[0] if row else 0
        except sqlite3.Error as e:
            raise CacheError(f"SQLite cache count error: {e}") from e

    def close(self) -> None:
        """Close SQLite database connection and release file locks."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                finally:
                    self._conn = None

    def __enter__(self) -> SQLiteCache:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

