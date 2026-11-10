"""Cache interfaces and implementations for web search."""

from websearch_py.cache.base import BaseCache, normalize_query
from websearch_py.cache.memory import InMemoryCache
from websearch_py.cache.null import NullCache
from websearch_py.cache.sqlite import SQLiteCache

__all__ = [
    "BaseCache",
    "InMemoryCache",
    "NullCache",
    "SQLiteCache",
    "normalize_query",
]
