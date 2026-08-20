"""Null cache backend for disabling caching."""

from __future__ import annotations

from typing import Optional

from web_search.cache.base import BaseCache
from web_search.models import SearchResult


class NullCache(BaseCache):
    """No-op cache implementation that performs no caching."""

    def get(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
    ) -> Optional[list[SearchResult]]:
        return None

    def set(
        self,
        query: str,
        results: list[SearchResult],
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> None:
        pass

    def delete(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
    ) -> bool:
        return False

    def clear(self) -> None:
        pass

    def purge_expired(self) -> int:
        return 0
