"""Integration tests querying real search engine endpoints."""

import pytest
from web_search import WebSearcher, search, search_json
from web_search.cache import InMemoryCache


def is_online():
    import socket
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=2.0)
        return True
    except OSError:
        return False


@pytest.mark.skipif(not is_online(), reason="Internet connection not available")
def test_live_search_fallback_chain():
    searcher = WebSearcher(engines=["duckduckgo", "bing"], cache=False, timeout=15.0)
    resp = searcher.search("Rust programming language", max_results=3, language="en")

    assert resp.engine_used in ["duckduckgo", "duckduckgo_lite", "bing"]
    assert len(resp.results) > 0
    first = resp.results[0]
    assert first.titre
    assert first.url.startswith("http")
    assert first.extrait is not None


@pytest.mark.skipif(not is_online(), reason="Internet connection not available")
def test_live_search_bing():
    searcher = WebSearcher(engines=["bing"], cache=False, timeout=15.0)
    resp = searcher.search("Golang official documentation", max_results=3, language="en")

    assert resp.engine_used == "bing"
    assert len(resp.results) > 0
    first = resp.results[0]
    assert first.titre
    assert first.url.startswith("http")


@pytest.mark.skipif(not is_online(), reason="Internet connection not available")
def test_live_search_json_output():
    import json
    json_str = search_json("TypeScript tutorial", max_results=2, use_cache=False)
    data = json.loads(json_str)

    assert isinstance(data, list)
    assert len(data) >= 1
    assert "titre" in data[0]
    assert "url" in data[0]
    assert "extrait" in data[0]
    assert data[0]["url"].startswith("http")


@pytest.mark.skipif(not is_online(), reason="Internet connection not available")
def test_live_cache_hit_on_identical_query():
    cache = InMemoryCache()
    searcher = WebSearcher(engines=["duckduckgo", "bing"], cache=cache, timeout=15.0)

    # 1. First search -> Cache Miss
    resp1 = searcher.search("Python async await tutorial", max_results=3)
    assert resp1.cached is False
    engine_used = resp1.engine_used

    # 2. Second search with identical query (different casing/spacing) -> Cache Hit
    resp2 = searcher.search("  PYTHON Async Await Tutorial   ", max_results=3)
    assert resp2.cached is True
    assert resp2.engine_used == "cache"
    assert len(resp2.results) == len(resp1.results)
    assert resp2.results[0].url == resp1.results[0].url
    assert resp2.execution_time_ms < 50.0  # Instant cache retrieval (<50ms)
