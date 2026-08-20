"""Additional unit tests for edge cases and 100% core coverage."""

import time
import pytest
from unittest.mock import patch
from websearch_py.cache.base import BaseCache
from websearch_py.cache.memory import InMemoryCache
from websearch_py.cache.sqlite import SQLiteCache
from websearch_py.engines.base import BaseSearchEngine
from websearch_py.engines.registry import EngineRegistry
from websearch_py.exceptions import WebSearchError
from websearch_py.models import SearchResult, SearchResponse, RotationStrategy
from websearch_py.rotation import EngineRotator
from websearch_py.searcher import WebSearcher
from websearch_py.cli import main


class CustomTestEngine(BaseSearchEngine):
    name = "custom_test"
    def search(self, query, **kwargs):
        return [SearchResult(titre="Custom", url="https://custom.com", extrait="Custom desc")]


def test_base_cache_in_operator():
    cache = InMemoryCache()
    cache.set("python", [SearchResult(titre="T", url="https://t.com", extrait="S")])
    assert ("python" in cache) is True
    assert ("nonexistent" in cache) is False


def test_memory_cache_purge_expired():
    cache = InMemoryCache(default_ttl_seconds=1)
    res = [SearchResult(titre="T", url="https://t.com", extrait="S")]
    cache.set("q1", res, ttl=1)
    cache.set("q2", res, ttl=10)

    time.sleep(1.1)
    purged = cache.purge_expired()
    assert purged == 1
    assert cache.get("q1") is None
    assert cache.get("q2") is not None


def test_sqlite_cache_purge_and_size():
    cache = SQLiteCache(db_path=":memory:", default_ttl_seconds=1)
    res = [SearchResult(titre="T", url="https://t.com", extrait="S")]
    cache.set("q1", res, ttl=1)
    cache.set("q2", res, ttl=100)

    assert cache.size() >= 1
    time.sleep(1.1)
    purged = cache.purge_expired()
    assert purged == 1
    cache.close()


def test_base_search_engine_clean_url_patterns():
    engine = CustomTestEngine()

    # DuckDuckGo redirect
    ddg_url = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage%3Fa%3D1&rut=123"
    assert engine.clean_url(ddg_url) == "https://example.com/page?a=1"

    # Google redirect
    g_url = "/url?q=https://example.com/google&sa=U"
    assert engine.clean_url(g_url) == "https://example.com/google"

    # Bing base64 redirect
    # aHR0cHM6Ly9leGFtcGxlLmNvbS9iaW5n -> https://example.com/bing
    b_url = "https://www.bing.com/ck/a?!&&p=abc&u=a1aHR0cHM6Ly9leGFtcGxlLmNvbS9iaW5n&ntb=1"
    assert engine.clean_url(b_url) == "https://example.com/bing"

    # Yahoo redirect
    y_url = "https://r.search.yahoo.com/_ylt=Awr/RU=https%3a%2f%2fexample.com%2fyahoo/RK=2/RS=xyz"
    assert engine.clean_url(y_url) == "https://example.com/yahoo"

    # Protocol-relative URL
    proto_url = "//example.com/relative"
    assert engine.clean_url(proto_url) == "https://example.com/relative"

    # Invalid / empty
    assert engine.clean_url(None) is None
    assert engine.clean_url("") is None
    assert engine.clean_url("javascript:void(0)") is None


def test_engine_rotator_invalid_empty():
    with pytest.raises(ValueError):
        EngineRotator([])


def test_engine_rotator_single_engine():
    e = CustomTestEngine()
    rotator = EngineRotator([e], strategy=RotationStrategy.ROUND_ROBIN)
    assert rotator.get_ordered_engines() == [e]
    assert rotator.get_ordered_engines() == [e]


def test_engine_registry_custom_register_and_unknown():
    EngineRegistry.register("my_custom", CustomTestEngine)
    assert "custom_test" in EngineRegistry.list_available()
    inst = EngineRegistry.create("my_custom")
    assert isinstance(inst, CustomTestEngine)

    with pytest.raises(WebSearchError):
        EngineRegistry.get("non_existent_engine_name_12345")


def test_search_result_to_json_with_metadata():
    res = SearchResult(titre="Titre", url="https://url.com", extrait="Extrait", engine="bing", rank=3)
    json_meta = res.to_json(include_metadata=True)
    assert '"engine": "bing"' in json_meta
    assert '"rank": 3' in json_meta


def test_cli_save_to_file():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = str(Path(tmpdir) / "results.json")
        with patch("websearch_py.cli.WebSearcher.search") as mock_search:
            mock_search.return_value = SearchResponse(
                query="python",
                results=[SearchResult(titre="Python", url="https://python.org", extrait="Lang", engine="ddg", rank=1)],
                engine_used="duckduckgo",
            )
            ret = main(["python", "--json", "-o", out_file])
            assert ret == 0

        with open(out_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "https://python.org" in content


def test_websearcher_invalid_engine_type():
    with pytest.raises(TypeError):
        WebSearcher(engines=[12345])
