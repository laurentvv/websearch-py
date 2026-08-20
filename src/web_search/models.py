"""Data models for web search results and responses.

Provides standard structured results with `titre`, `url`, `extrait` (and aliases `title`, `snippet`),
as well as response wrappers with metadata (cache status, engine used, execution time).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class RotationStrategy(str, Enum):
    """Available engine rotation and fallback strategies."""
    FALLBACK_PRIORITY = "fallback_priority"  # Tries engines in exact configured order
    ROUND_ROBIN = "round_robin"              # Rotates starting engine on each query, then falls back
    RANDOM = "random"                        # Picks a random starting engine, then falls back
    FASTEST = "fastest"                      # Queries engines concurrently and returns first successful


class EngineName(str, Enum):
    """Supported built-in search engines."""
    DUCKDUCKGO = "duckduckgo"
    DUCKDUCKGO_LITE = "duckduckgo_lite"
    BING = "bing"
    GOOGLE = "google"
    YAHOO = "yahoo"
    QWANT = "qwant"
    BRAVE = "brave"
    MOJEEK = "mojeek"


@dataclass
class SearchResult:
    """Individual web search result.

    Attributes:
        titre: Result page title (also accessible via .title)
        url: Target web page URL
        extrait: Text snippet/description (also accessible via .snippet)
        engine: The search engine that found this result
        rank: Rank position in results (1-indexed)
        extra: Optional additional metadata (dates, icons, etc.)
    """

    titre: str
    url: str
    extrait: str
    engine: str = "unknown"
    rank: int = 1
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def title(self) -> str:
        """English alias for titre."""
        return self.titre

    @property
    def snippet(self) -> str:
        """English alias for extrait."""
        return self.extrait

    def to_dict(self, include_metadata: bool = True) -> dict[str, Any]:
        """Convert search result to dictionary.

        Args:
            include_metadata: If True, include engine, rank, and extra metadata.
                             If False, returns only titre, url, extrait.
        """
        if include_metadata:
            return {
                "titre": self.titre,
                "url": self.url,
                "extrait": self.extrait,
                "engine": self.engine,
                "rank": self.rank,
                "extra": self.extra,
            }
        return {
            "titre": self.titre,
            "url": self.url,
            "extrait": self.extrait,
        }

    def to_json(self, include_metadata: bool = False, indent: Optional[int] = 2) -> str:
        """Serialize result to JSON string."""
        return json.dumps(
            self.to_dict(include_metadata=include_metadata),
            ensure_ascii=False,
            indent=indent,
        )


@dataclass
class SearchResponse:
    """Complete search response containing results and execution metadata.

    Attributes:
        query: The normalized search query
        results: List of SearchResult items
        engine_used: Name of the engine that successfully returned results
        cached: True if the result was retrieved from cache
        execution_time_ms: Total time taken in milliseconds
        fallback_history: List of engines attempted before success
        timestamp: ISO timestamp of response creation
    """

    query: str
    results: list[SearchResult] = field(default_factory=list)
    engine_used: str = "none"
    cached: bool = False
    execution_time_ms: float = 0.0
    fallback_history: list[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __len__(self) -> int:
        return len(self.results)

    def __getitem__(self, index: int) -> SearchResult:
        return self.results[index]

    def __iter__(self):
        return iter(self.results)

    @property
    def total_results(self) -> int:
        """Total number of results returned."""
        return len(self.results)

    def to_dict(self, detailed: bool = True) -> dict[str, Any]:
        """Convert response to dictionary.

        Args:
            detailed: If True, include full metadata (engine, fallback history, etc.).
                      If False, returns a clean dict with query and results.
        """
        results_data = [r.to_dict(include_metadata=detailed) for r in self.results]
        if detailed:
            return {
                "query": self.query,
                "engine_used": self.engine_used,
                "cached": self.cached,
                "execution_time_ms": round(self.execution_time_ms, 2),
                "total_results": len(self.results),
                "fallback_history": self.fallback_history,
                "timestamp": self.timestamp,
                "results": results_data,
            }
        return {
            "query": self.query,
            "results": results_data,
        }

    def to_json(self, detailed: bool = False, indent: Optional[int] = 2) -> str:
        """Serialize search response to JSON string.

        Args:
            detailed: If True, outputs full search metadata.
                      If False, outputs clean list of results with [titre, url, extrait].
            indent: Indentation spaces for pretty-printing (default: 2, None for compact).
        """
        if detailed:
            data = self.to_dict(detailed=True)
        else:
            # Clean list of results directly: [{"titre": ..., "url": ..., "extrait": ...}, ...]
            data = [r.to_dict(include_metadata=False) for r in self.results]

        return json.dumps(data, ensure_ascii=False, indent=indent)
