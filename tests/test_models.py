"""Tests for SearchResult and SearchResponse data models."""

import json

from websearch_py.models import SearchResponse, SearchResult


def test_search_result_attributes_and_aliases():
    result = SearchResult(
        titre="Python Official",
        url="https://www.python.org",
        extrait="The official Python website.",
        engine="duckduckgo",
        rank=1,
    )

    # French & English property access
    assert result.titre == "Python Official"
    assert result.title == "Python Official"
    assert result.url == "https://www.python.org"
    assert result.extrait == "The official Python website."
    assert result.snippet == "The official Python website."
    assert result.engine == "duckduckgo"
    assert result.rank == 1


def test_search_result_to_dict():
    result = SearchResult(
        titre="Test Title",
        url="https://example.com",
        extrait="Sample snippet",
        engine="bing",
        rank=2,
    )

    clean_dict = result.to_dict(include_metadata=False)
    assert clean_dict == {
        "titre": "Test Title",
        "url": "https://example.com",
        "extrait": "Sample snippet",
    }

    full_dict = result.to_dict(include_metadata=True)
    assert full_dict["engine"] == "bing"
    assert full_dict["rank"] == 2


def test_search_response_to_json_clean_format():
    res1 = SearchResult(titre="Site 1", url="https://site1.com", extrait="Extrait 1", engine="ddg", rank=1)
    res2 = SearchResult(titre="Site 2", url="https://site2.com", extrait="Extrait 2", engine="ddg", rank=2)
    resp = SearchResponse(
        query="python",
        results=[res1, res2],
        engine_used="duckduckgo",
        cached=False,
        execution_time_ms=120.5,
    )

    # Clean standard JSON format: list of [{titre, url, extrait}]
    json_str = resp.to_json(detailed=False)
    parsed = json.loads(json_str)

    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert parsed[0] == {
        "titre": "Site 1",
        "url": "https://site1.com",
        "extrait": "Extrait 1",
    }
    assert parsed[1] == {
        "titre": "Site 2",
        "url": "https://site2.com",
        "extrait": "Extrait 2",
    }


def test_search_response_to_json_detailed_format():
    res = SearchResult(titre="Python", url="https://python.org", extrait="Language", engine="bing", rank=1)
    resp = SearchResponse(
        query="python",
        results=[res],
        engine_used="bing",
        cached=True,
        execution_time_ms=5.2,
        fallback_history=["duckduckgo", "bing"],
    )

    json_str = resp.to_json(detailed=True)
    parsed = json.loads(json_str)

    assert parsed["query"] == "python"
    assert parsed["engine_used"] == "bing"
    assert parsed["cached"] is True
    assert parsed["execution_time_ms"] == 5.2
    assert parsed["total_results"] == 1
    assert parsed["fallback_history"] == ["duckduckgo", "bing"]
    assert len(parsed["results"]) == 1


def test_search_response_iteration_and_indexing():
    results = [
        SearchResult(titre=f"Title {i}", url=f"https://example{i}.com", extrait=f"Snippet {i}") for i in range(3)
    ]
    resp = SearchResponse(query="test", results=results)

    assert len(resp) == 3
    assert resp.total_results == 3
    assert resp[0].titre == "Title 0"
    assert [r.titre for r in resp] == ["Title 0", "Title 1", "Title 2"]
