"""Base cache interface and key generation for web search queries."""

from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from websearch_py.models import SearchResult


def normalize_query(query: str) -> str:
    """Normalize query string for consistent cache key generation."""
    # Strip whitespace, collapse multiple spaces, convert to lowercase
    cleaned = re.sub(r"\s+", " ", query.strip().lower())
    return cleaned


class BaseCache(ABC):
    """Abstract base class for search caching backends."""

    def __init__(self, default_ttl_seconds: int = 3600):
        """Initialize cache.

        Args:
            default_ttl_seconds: Cache item Time-To-Live in seconds (default: 1 hour).
        """
        self.default_ttl_seconds = default_ttl_seconds

    def make_key(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
    ) -> str:
        """Generate a deterministic cache key from search parameters.

        Args:
            query: The search term
            max_results: Maximum requested items
            language: Language code
            region: Optional country/region code

        Returns:
            SHA256 hex string cache key.
        """
        normalized_q = normalize_query(query)
        payload = {
            "q": normalized_q,
            "n": max_results,
            "hl": language.lower() if language else "en",
            "gl": region.lower() if region else "",
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @abstractmethod
    def get(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
    ) -> Optional[list[SearchResult]]:
        """Retrieve cached search results if available and not expired."""
        pass

    @abstractmethod
    def set(
        self,
        query: str,
        results: list[SearchResult],
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """Store search results in cache with TTL."""
        pass

    @abstractmethod
    def delete(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
    ) -> bool:
        """Delete specific search results from cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries from the cache."""
        pass

    @abstractmethod
    def purge_expired(self) -> int:
        """Remove all expired cache entries and return count of removed items."""
        pass

    def __contains__(self, query: str) -> bool:
        return self.get(query) is not None
