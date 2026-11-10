"""In-memory cache implementation with TTL and LRU eviction."""

from __future__ import annotations

import collections
import threading
import time

from websearch_py.cache.base import BaseCache
from websearch_py.models import SearchResult


class InMemoryCache(BaseCache):
    """Thread-safe In-Memory cache with TTL expiration and LRU eviction."""

    def __init__(self, default_ttl_seconds: int = 3600, max_entries: int = 1000):
        """Initialize in-memory cache.

        Args:
            default_ttl_seconds: TTL in seconds (default: 3600s / 1h).
            max_entries: Maximum number of distinct queries to store before LRU eviction.
        """
        super().__init__(default_ttl_seconds=default_ttl_seconds)
        self.max_entries = max_entries
        self._cache: collections.OrderedDict[str, tuple[float, list[SearchResult]]] = collections.OrderedDict()
        self._lock = threading.RLock()

    def get(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: str | None = None,
    ) -> list[SearchResult] | None:
        """Retrieve cached search results if valid and not expired."""
        key = self.make_key(query, max_results, language, region)
        now = time.time()

        with self._lock:
            if key not in self._cache:
                return None

            expires_at, results = self._cache[key]
            if now >= expires_at:
                # Expired: remove and return None
                del self._cache[key]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return list(results)

    def set(
        self,
        query: str,
        results: list[SearchResult],
        max_results: int = 10,
        language: str = "en",
        region: str | None = None,
        ttl: int | None = None,
    ) -> None:
        """Store results in memory cache."""
        key = self.make_key(query, max_results, language, region)
        ttl_seconds = ttl if ttl is not None else self.default_ttl_seconds
        expires_at = time.time() + ttl_seconds

        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (expires_at, list(results))

            # Evict oldest if exceeding max_entries
            while len(self._cache) > self.max_entries:
                self._cache.popitem(last=False)

    def delete(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: str | None = None,
    ) -> bool:
        """Delete query from memory cache."""
        key = self.make_key(query, max_results, language, region)
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all in-memory entries."""
        with self._lock:
            self._cache.clear()

    def purge_expired(self) -> int:
        """Remove all expired cache entries and return count."""
        now = time.time()
        purged = 0
        with self._lock:
            expired_keys = [k for k, (exp, _) in self._cache.items() if now >= exp]
            for k in expired_keys:
                del self._cache[k]
                purged += 1
        return purged

    def size(self) -> int:
        """Return the current number of cached items."""
        with self._lock:
            return len(self._cache)
