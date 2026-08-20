"""Tests for individual search engine scrapers using mocked HTTP responses."""

import responses
import pytest
from websearch_py.engines import (
    DuckDuckGoEngine,
    DuckDuckGoLiteEngine,
    BingEngine,
    GoogleEngine,
    YahooEngine,
    QwantEngine,
    BraveEngine,
    MojeekEngine,
    EngineRegistry,
)
from websearch_py.exceptions import EngineError, RateLimitError
from tests.conftest import (
    SAMPLE_DDG_HTML,
    SAMPLE_DDG_LITE_HTML,
    SAMPLE_BING_HTML,
    SAMPLE_GOOGLE_HTML,
    SAMPLE_YAHOO_HTML,
    SAMPLE_QWANT_API_JSON,
    SAMPLE_BRAVE_HTML,
    SAMPLE_MOJEEK_HTML,
)


@responses.activate
def test_duckduckgo_html_parsing():
    responses.add(
        responses.POST,
        "https://html.duckduckgo.com/html/",
        body=SAMPLE_DDG_HTML,
        status=200,
    )

    engine = DuckDuckGoEngine()
    results = engine.search("python", max_results=5)

    assert len(results) == 2
    assert results[0].titre == "Welcome to Python.org"
    assert results[0].url == "https://www.python.org/"
    assert "official home" in results[0].extrait
    assert results[0].engine == "duckduckgo"
    assert results[0].rank == 1

    assert results[1].titre == "Python 3 Documentation"
    assert results[1].url == "https://docs.python.org/3/"


@responses.activate
def test_duckduckgo_lite_fallback_on_empty_html():
    # Primary returns 200 with no results, fallback returns results
    responses.add(
        responses.POST,
        "https://html.duckduckgo.com/html/",
        body="<html><body>No results</body></html>",
        status=200,
    )
    responses.add(
        responses.POST,
        "https://lite.duckduckgo.com/lite/",
        body=SAMPLE_DDG_LITE_HTML,
        status=200,
    )

    engine = DuckDuckGoEngine()
    results = engine.search("fastapi", max_results=5)

    assert len(results) == 1
    assert results[0].titre == "FastAPI Framework"
    assert results[0].url == "https://fastapi.tiangolo.com/"
    assert "modern, fast" in results[0].extrait


@responses.activate
def test_bing_html_parsing_and_base64_url_decoding():
    responses.add(
        responses.GET,
        "https://www.bing.com/search",
        body=SAMPLE_BING_HTML,
        status=200,
    )

    engine = BingEngine()
    results = engine.search("python", max_results=5)

    assert len(results) == 2
    # Check that base64 encoded URL was decoded properly to python.org
    assert results[0].titre == "Welcome to Python.org"
    assert results[0].url == "https://www.python.org/"
    assert results[0].engine == "bing"

    assert results[1].titre == "The Python Tutorial"
    assert results[1].url == "https://docs.python.org/tutorial/"


@responses.activate
def test_google_html_parsing():
    responses.add(
        responses.GET,
        "https://www.google.com/search",
        body=SAMPLE_GOOGLE_HTML,
        status=200,
    )

    engine = GoogleEngine()
    results = engine.search("python", max_results=5)

    assert len(results) == 2
    assert results[0].titre == "Python Official Website"
    assert results[0].url == "https://www.python.org/"
    assert "programming language" in results[0].extrait
    assert results[0].engine == "google"

    assert results[1].titre == "PyPI - The Python Package Index"
    assert results[1].url == "https://pypi.org/"


@responses.activate
def test_yahoo_html_parsing():
    responses.add(
        responses.GET,
        "https://search.yahoo.com/search",
        body=SAMPLE_YAHOO_HTML,
        status=200,
    )

    engine = YahooEngine()
    results = engine.search("python", max_results=5)

    assert len(results) == 1
    assert results[0].titre == "Welcome to Python.org"
    assert results[0].url == "https://www.python.org/"
    assert results[0].engine == "yahoo"


@responses.activate
def test_qwant_api_parsing():
    responses.add(
        responses.GET,
        "https://api.qwant.com/v3/search/web",
        json=SAMPLE_QWANT_API_JSON,
        status=200,
    )

    engine = QwantEngine()
    results = engine.search("python", max_results=5)

    assert len(results) == 1
    assert results[0].titre == "Python Language"
    assert results[0].url == "https://www.python.org/"
    assert results[0].engine == "qwant"


@responses.activate
def test_brave_html_parsing():
    responses.add(
        responses.GET,
        "https://search.brave.com/search",
        body=SAMPLE_BRAVE_HTML,
        status=200,
    )

    engine = BraveEngine()
    results = engine.search("python", max_results=5)

    assert len(results) == 1
    assert results[0].titre == "Welcome to Python"
    assert results[0].url == "https://www.python.org/"


@responses.activate
def test_mojeek_html_parsing():
    responses.add(
        responses.GET,
        "https://www.mojeek.com/search",
        body=SAMPLE_MOJEEK_HTML,
        status=200,
    )

    engine = MojeekEngine()
    results = engine.search("python", max_results=5)

    assert len(results) == 1
    assert results[0].titre == "Welcome to Python.org"
    assert results[0].url == "https://www.python.org/"


@responses.activate
def test_rate_limit_error_handling():
    responses.add(
        responses.POST,
        "https://html.duckduckgo.com/html/",
        status=429,
    )
    responses.add(
        responses.POST,
        "https://lite.duckduckgo.com/lite/",
        status=429,
    )

    engine = DuckDuckGoEngine()
    with pytest.raises(RateLimitError):
        engine.search("blocked query")


def test_engine_registry():
    available = EngineRegistry.list_available()
    assert "duckduckgo" in available
    assert "bing" in available
    assert "google" in available

    inst = EngineRegistry.create("ddg", timeout=5.0)
    assert isinstance(inst, DuckDuckGoEngine)
    assert inst.timeout == 5.0
