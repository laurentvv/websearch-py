"""Tests for WebSearcher coordinator, fallback, rotation, and cache management."""

import json

import pytest

from websearch_py.cache import InMemoryCache
from websearch_py.engines.base import BaseSearchEngine
from websearch_py.exceptions import AllEnginesFailedError, EngineError, RateLimitError
from websearch_py.models import RotationStrategy, SearchResult
from websearch_py.searcher import WebSearcher, search, search_json


class MockEngine(BaseSearchEngine):
    def __init__(self, name: str, results: list[SearchResult] | None = None, fail_with: Exception | None = None):
        super().__init__()
        self.name = name
        self.results = results or []
        self.fail_with = fail_with
        self.call_count = 0

    def search(self, query, max_results=10, language="fr", region=None):
        self.call_count += 1
        if self.fail_with:
            raise self.fail_with
        return self.results[:max_results]


def test_searcher_successful_primary():
    res = [SearchResult(titre="Python", url="https://python.org", extrait="Snippet", engine="ddg", rank=1)]
    eng1 = MockEngine("ddg", results=res)
    eng2 = MockEngine("bing", results=[])

    searcher = WebSearcher(engines=[eng1, eng2], cache=True)
    resp = searcher.search("python")

    assert resp.engine_used == "ddg"
    assert resp.cached is False
    assert len(resp.results) == 1
    assert resp.results[0].titre == "Python"
    assert eng1.call_count == 1
    assert eng2.call_count == 0


def test_searcher_cache_hit():
    res = [SearchResult(titre="Python", url="https://python.org", extrait="Snippet", engine="ddg", rank=1)]
    eng1 = MockEngine("ddg", results=res)

    cache = InMemoryCache()
    searcher = WebSearcher(engines=[eng1], cache=cache)

    # First call: cache miss
    resp1 = searcher.search("python")
    assert resp1.cached is False
    assert eng1.call_count == 1

    # Second call with identical query: cache hit
    resp2 = searcher.search("  PYTHON  ")
    assert resp2.cached is True
    assert resp2.engine_used == "cache"
    assert len(resp2.results) == 1
    # Engine was NOT called again
    assert eng1.call_count == 1


def test_searcher_fallback_on_error():
    # Engine 1 fails with RateLimitError, Engine 2 succeeds
    eng1 = MockEngine("ddg", fail_with=RateLimitError("ddg", "429 Too Many Requests"))
    res_bing = [
        SearchResult(titre="Bing Result", url="https://bing.com/res", extrait="Bing Snip", engine="bing", rank=1)
    ]
    eng2 = MockEngine("bing", results=res_bing)

    searcher = WebSearcher(engines=[eng1, eng2], cache=False)
    resp = searcher.search("query")

    assert resp.engine_used == "bing"
    assert len(resp.results) == 1
    assert resp.results[0].titre == "Bing Result"
    assert eng1.call_count == 1
    assert eng2.call_count == 1
    assert resp.fallback_history == ["ddg", "bing"]


def test_searcher_fallback_on_zero_results():
    # Engine 1 returns empty list, Engine 2 succeeds
    eng1 = MockEngine("ddg", results=[])
    res_bing = [
        SearchResult(titre="Bing Result", url="https://bing.com/res", extrait="Bing Snip", engine="bing", rank=1)
    ]
    eng2 = MockEngine("bing", results=res_bing)

    searcher = WebSearcher(engines=[eng1, eng2], cache=False)
    resp = searcher.search("query")

    assert resp.engine_used == "bing"
    assert len(resp.results) == 1
    assert eng1.call_count == 1
    assert eng2.call_count == 1


def test_searcher_all_engines_failed():
    eng1 = MockEngine("ddg", fail_with=RateLimitError("ddg", "429"))
    eng2 = MockEngine("bing", fail_with=EngineError("bing", "Timeout"))

    searcher = WebSearcher(engines=[eng1, eng2], cache=False)
    with pytest.raises(AllEnginesFailedError) as exc_info:
        searcher.search("fail query")

    assert "All engines failed" in str(exc_info.value)
    assert "fail query" in str(exc_info.value)


def test_searcher_round_robin_rotation():
    res_ddg = [SearchResult(titre="DDG Res", url="https://ddg.com", extrait="DDG", engine="ddg", rank=1)]
    res_bing = [SearchResult(titre="Bing Res", url="https://bing.com", extrait="Bing", engine="bing", rank=1)]

    eng1 = MockEngine("ddg", results=res_ddg)
    eng2 = MockEngine("bing", results=res_bing)

    searcher = WebSearcher(
        engines=[eng1, eng2],
        strategy=RotationStrategy.ROUND_ROBIN,
        cache=False,
    )

    # First query -> uses eng1 (DDG)
    r1 = searcher.search("query 1")
    assert r1.engine_used == "ddg"

    # Second query -> starts with eng2 (Bing)
    r2 = searcher.search("query 2")
    assert r2.engine_used == "bing"


def test_search_json_output_format():
    res = [
        SearchResult(
            titre="FastAPI", url="https://fastapi.tiangolo.com", extrait="Web framework", engine="ddg", rank=1
        ),
        SearchResult(
            titre="Django",
            url="https://djangoproject.com",
            extrait="Web framework for perfectionists",
            engine="ddg",
            rank=2,
        ),
    ]
    eng = MockEngine("ddg", results=res)
    searcher = WebSearcher(engines=[eng], cache=False)

    json_output = searcher.search_json("python frameworks", detailed=False)
    parsed = json.loads(json_output)

    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert parsed[0] == {
        "titre": "FastAPI",
        "url": "https://fastapi.tiangolo.com",
        "extrait": "Web framework",
    }
    assert parsed[1] == {
        "titre": "Django",
        "url": "https://djangoproject.com",
        "extrait": "Web framework for perfectionists",
    }


def test_search_json_detailed_output():
    res = [SearchResult(titre="Python", url="https://python.org", extrait="Language", engine="ddg", rank=1)]
    eng = MockEngine("ddg", results=res)
    searcher = WebSearcher(engines=[eng], cache=False)

    json_output = searcher.search_json("python", detailed=True)
    parsed = json.loads(json_output)

    assert isinstance(parsed, dict)
    assert parsed["query"] == "python"
    assert parsed["engine_used"] == "ddg"
    assert parsed["cached"] is False
    assert len(parsed["results"]) == 1


def test_searcher_fastest_strategy():
    res1 = [SearchResult(titre="Fastest Res", url="https://fast.com", extrait="Fast", engine="eng1", rank=1)]
    res2 = [SearchResult(titre="Slow Res", url="https://slow.com", extrait="Slow", engine="eng2", rank=1)]

    eng1 = MockEngine("eng1", results=res1)
    eng2 = MockEngine("eng2", results=res2)

    searcher = WebSearcher(
        engines=[eng1, eng2],
        strategy=RotationStrategy.FASTEST,
        cache=False,
    )
    resp = searcher.search("speed test")

    assert resp.cached is False
    assert len(resp.results) == 1
    assert resp.engine_used in ["eng1", "eng2"]


def test_search_top_level_convenience_function():
    res = [SearchResult(titre="Python", url="https://python.org", extrait="Lang", engine="mock_ddg", rank=1)]
    eng = MockEngine("mock_ddg", results=res)

    resp = search("Python", engines=[eng], use_cache=False)
    assert resp.total_results == 1
    assert resp.results[0].titre == "Python"
    assert resp.engine_used == "mock_ddg"

    json_str = search_json("Python", engines=[eng], detailed=False, use_cache=False)
    data = json.loads(json_str)
    assert isinstance(data, list)
    assert data[0]["titre"] == "Python"
    assert data[0]["url"] == "https://python.org"
    assert data[0]["extrait"] == "Lang"


def test_searcher_empty_query_raises():
    searcher = WebSearcher(engines=["duckduckgo"], cache=False)
    with pytest.raises(ValueError):
        searcher.search("   ")
