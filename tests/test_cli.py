"""Tests for CLI interface."""

import json
from unittest.mock import patch

from websearch_py.cli import main
from websearch_py.models import SearchResponse, SearchResult


def test_cli_list_engines(capsys):
    ret = main(["--list-engines"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "duckduckgo" in captured.out
    assert "bing" in captured.out
    assert "google" in captured.out


def test_cli_empty_query(capsys):
    ret = main([])
    assert ret == 1


@patch("websearch_py.cli.WebSearcher.search")
def test_cli_search_json_output(mock_search, capsys):
    mock_results = [
        SearchResult(titre="FastAPI", url="https://fastapi.tiangolo.com", extrait="Framework", engine="ddg", rank=1)
    ]
    mock_search.return_value = SearchResponse(
        query="fastapi",
        results=mock_results,
        engine_used="duckduckgo",
        cached=False,
    )

    ret = main(["fastapi", "--json", "--no-cache"])
    assert ret == 0
    captured = capsys.readouterr()

    parsed = json.loads(captured.out)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["titre"] == "FastAPI"
    assert parsed[0]["url"] == "https://fastapi.tiangolo.com"
    assert parsed[0]["extrait"] == "Framework"


@patch("websearch_py.cli.WebSearcher.search")
def test_cli_search_detailed_output(mock_search, capsys):
    mock_results = [SearchResult(titre="Python", url="https://python.org", extrait="Lang", engine="ddg", rank=1)]
    mock_search.return_value = SearchResponse(
        query="python",
        results=mock_results,
        engine_used="duckduckgo",
        cached=True,
    )

    ret = main(["python", "--detailed"])
    assert ret == 0
    captured = capsys.readouterr()

    parsed = json.loads(captured.out)
    assert isinstance(parsed, dict)
    assert parsed["query"] == "python"
    assert parsed["cached"] is True


def test_cli_clear_cache(capsys):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = str(Path(tmpdir) / "temp_cache.db")
        ret = main(["--clear-cache", "--cache-db", db_file])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Cache cleared successfully" in captured.out
