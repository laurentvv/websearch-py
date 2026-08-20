"""Tests for cache backends (InMemoryCache, SQLiteCache, NullCache)."""

import time
from websearch_py.cache import InMemoryCache, NullCache, SQLiteCache, normalize_query
from websearch_py.models import SearchResult


def test_query_normalization():
    assert normalize_query("  Python   Programming  ") == "python programming"
    assert normalize_query("PYTHON\n\tTutorial") == "python tutorial"


def test_in_memory_cache_basic_operations():
    cache = InMemoryCache(default_ttl_seconds=60)
    results = [
        SearchResult(titre="Test", url="https://test.com", extrait="Snip", engine="ddg", rank=1)
    ]

    # Cache miss
    assert cache.get("python") is None

    # Set and cache hit
    cache.set("python", results)
    cached = cache.get("python")
    assert cached is not None
    assert len(cached) == 1
    assert cached[0].titre == "Test"

    # Query normalisation hit
    assert cache.get("  PYTHON   ") is not None

    # Delete
    assert cache.delete("python") is True
    assert cache.get("python") is None

    # Clear
    cache.set("query1", results)
    cache.set("query2", results)
    assert cache.size() == 2
    cache.clear()
    assert cache.size() == 0


def test_in_memory_cache_ttl_expiration():
    # Cache with 1 second TTL
    cache = InMemoryCache(default_ttl_seconds=1)
    results = [SearchResult(titre="T", url="https://t.com", extrait="S")]

    cache.set("query", results, ttl=1)
    assert cache.get("query") is not None

    time.sleep(1.1)
    # Expired
    assert cache.get("query") is None


def test_in_memory_cache_lru_eviction():
    # Cache with max 2 entries
    cache = InMemoryCache(default_ttl_seconds=60, max_entries=2)
    res = [SearchResult(titre="T", url="https://t.com", extrait="S")]

    cache.set("q1", res)
    cache.set("q2", res)
    assert cache.size() == 2

    # Access q1 to make q2 oldest
    _ = cache.get("q1")

    # Add q3, should evict q2
    cache.set("q3", res)
    assert cache.size() == 2
    assert cache.get("q1") is not None
    assert cache.get("q3") is not None
    assert cache.get("q2") is None


def test_sqlite_cache_in_memory():
    cache = SQLiteCache(db_path=":memory:", default_ttl_seconds=60)
    results = [
        SearchResult(titre="SQLite Test", url="https://sqlite.org", extrait="Embedded DB", engine="bing", rank=1)
    ]

    # Miss
    assert cache.get("database") is None

    # Set and hit
    cache.set("database", results)
    cached = cache.get("database")
    assert cached is not None
    assert len(cached) == 1
    assert cached[0].titre == "SQLite Test"
    assert cached[0].url == "https://sqlite.org"

    # Delete
    assert cache.delete("database") is True
    assert cache.get("database") is None


def test_sqlite_cache_persistence():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_cache.db"
        with SQLiteCache(db_path=db_file, default_ttl_seconds=3600) as cache1:
            results = [
                SearchResult(titre="Persist", url="https://persist.com", extrait="Snippet")
            ]
            cache1.set("persistent query", results)

        # Re-open in a separate instance
        with SQLiteCache(db_path=db_file, default_ttl_seconds=3600) as cache2:
            cached = cache2.get("persistent query")
            assert cached is not None
            assert len(cached) == 1
            assert cached[0].titre == "Persist"


def test_null_cache():
    cache = NullCache()
    results = [SearchResult(titre="T", url="https://t.com", extrait="S")]

    assert cache.get("query") is None
    cache.set("query", results)
    assert cache.get("query") is None
    assert cache.delete("query") is False
    assert cache.purge_expired() == 0
