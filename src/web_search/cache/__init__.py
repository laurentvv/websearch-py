"""Cache interfaces and implementations for web search."""

from web_search.cache.base import BaseCache, normalize_query
from web_search.cache.memory import InMemoryCache
from web_search.cache.null import NullCache
from web_search.cache.sqlite import SQLiteCache

__all__ = [
    "BaseCache",
    "InMemoryCache",
    "SQLiteCache",
    "NullCache",
    "normalize_query",
]
