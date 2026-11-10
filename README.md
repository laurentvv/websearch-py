<div align="center">

<img src="https://raw.githubusercontent.com/laurentvv/websearch-py/main/assets/banner.png" alt="websearch-py Banner" width="100%" style="border-radius: 8px; margin-bottom: 20px;" />

# ⚡ websearch-py

**Resilient multi-engine web search scraper with automatic fallback, engine rotation, smart caching, and standardized JSON output.**

[![PyPI Version](https://img.shields.io/pypi/v/websearch-py.svg?style=flat-square&color=blue)](https://pypi.org/project/websearch-py/)
[![Python Version](https://img.shields.io/badge/python-3.14%2B-blue.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![uv Managed](https://img.shields.io/badge/managed_by-uv-DE5FE9.svg?style=flat-square&logo=astral&logoColor=white)](https://github.com/astral-sh/uv)
[![Test Suite](https://img.shields.io/badge/tests-55%20passed-brightgreen.svg?style=flat-square&logo=pytest&logoColor=white)](https://github.com/laurentvv/websearch-py/tree/main/tests)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://github.com/laurentvv/websearch-py/blob/main/LICENSE)

[Features](#-key-features) • [Installation](#-installation) • [Quickstart](#-quickstart) • [CLI Usage](#-command-line-interface-cli) • [Architecture](#-architecture) • [Custom Engines](#-custom-search-engines)

</div>

---

## 🌟 Key Features

- 🔄 **Intelligent Fallback & Rotation**:
  - **Priority Fallback (`FALLBACK_PRIORITY`)**: Queries engines sequentially in priority order. If an engine fails (HTTP 429 rate limit, 202 challenge, CAPTCHA, timeout, or 0 results), the next engine seamlessly takes over.
  - **Round-Robin Load Distribution (`ROUND_ROBIN`)**: Circularly shifts the initial search engine for each incoming query to balance traffic across providers.
  - **Random Rotation (`RANDOM`)**: Picks a randomized starting engine with subsequent fallback.
  - **Concurrent Fastest (`FASTEST`)**: Dispatches queries in parallel across worker threads and returns the fastest valid engine response.
- ⚡ **Zero-Latency Smart Cache (< 1ms)**:
  - **In-Memory Cache (`InMemoryCache`)**: Thread-safe with configurable TTL (Time-To-Live) and LRU (Least-Recently-Used) eviction.
  - **Persistent SQLite Cache (`SQLiteCache`)**: Disk-backed cache with WAL mode, B-Tree indexes, and automated expired entry purging.
  - **Query Normalization**: Canonical query sanitization (case folding, whitespace collapsing) guarantees instant cache hits for duplicate queries.
- 🌐 **Built-in Search Engine Providers**:
  - **DuckDuckGo** (HTML & Lite endpoints with direct redirect unwrapping)
  - **Bing** (HTML scraper with automatic Base64 redirect decoding `u=a1...`)
  - **Google** (Desktop & Basic HTML layouts with EU consent cookie bypass)
  - **Yahoo Search**
  - **Qwant** (API & Lite scraper)
  - **Brave Search**
  - **Mojeek** (Independent index)
- 📦 **Standardized JSON Output**:
  - Clean standardized output schema: `titre`, `url`, `extrait` (with English aliases `title`, `snippet`).
  - Direct JSON serializer function (`search_json()`) or structured model (`SearchResult`, `SearchResponse`).
- 🛠️ **Developer Ergonomics**:
  - Full **Python 3.14+** support and managed via [**uv**](https://github.com/astral-sh/uv).
  - Modern typing with `py.typed` compliance.
  - Interactive CLI (`websearch` / `websearch-py`).

---

## 📥 Installation

```bash
# Install via uv / pip
uv add websearch-py
# or
pip install websearch-py
```

Or clone the repository from source:

```bash
# Clone repository
git clone https://github.com/laurentvv/websearch-py.git
cd websearch-py

# Sync dependencies and set up virtual environment
uv sync
```

---

## 🚀 Quickstart

### 1. Basic Python Search

```python
from web_search import search

# Perform a web search with automatic fallback and caching enabled
response = search("Python 3.14 new features", max_results=5, language="en")

print(f"Engine Used  : {response.engine_used}")
print(f"From Cache   : {response.cached}")
print(f"Elapsed Time : {response.execution_time_ms:.1f}ms")
print(f"Total Results: {len(response.results)}\n")

for item in response.results:
    print(f"[{item.rank}] {item.titre}")
    print(f"    URL    : {item.url}")
    print(f"    Snippet: {item.extrait}\n")
```

---

### 2. Direct Standard JSON Output

```python
from web_search import search_json

# Export clean JSON array of [{titre, url, extrait}]
json_data = search_json("FastAPI web framework tutorial", max_results=3, indent=2)
print(json_data)
```

**JSON Output:**
```json
[
  {
    "titre": "FastAPI Framework",
    "url": "https://fastapi.tiangolo.com/",
    "extrait": "FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.8+ based on standard Python type hints."
  },
  {
    "titre": "FastAPI Tutorial - W3Schools",
    "url": "https://www.w3schools.com/python/python_fastapi.asp",
    "extrait": "Learn how to use FastAPI to build web APIs with Python. Step-by-step tutorial with code examples and interactive exercises."
  }
]
```

To include execution metadata (engine used, cache status, latency, fallback history):
```python
detailed_json = search_json("FastAPI tutorial", detailed=True, indent=2)
print(detailed_json)
```

---

### 3. Advanced Configuration (`WebSearcher`)

```python
from web_search import WebSearcher, RotationStrategy, SQLiteCache

# Configure orchestrator with Round-Robin rotation and persistent SQLite cache
searcher = WebSearcher(
    engines=["duckduckgo", "bing", "yahoo", "google", "qwant"],
    strategy=RotationStrategy.ROUND_ROBIN,
    cache=SQLiteCache(db_path="search_cache.db", default_ttl_seconds=86400), # 24h TTL
    timeout=10.0,
)

# 1st query: network fetch with engine rotation
r1 = searcher.search("Machine Learning Python")

# 2nd identical query: instant response served from SQLite cache (< 1ms)
r2 = searcher.search("  MACHINE LEARNING Python   ")
assert r2.cached is True
```

---

## 💻 Command Line Interface (CLI)

The library provides the `websearch` executable:

```bash
# Human-readable formatted search
uv run websearch "Python 3.14" -n 5

# Output as clean standard JSON
uv run websearch "tetris html css js" -n 5 --json

# Detailed JSON with metadata (engine used, latency, cache status)
uv run websearch "DuckDB documentation" --detailed

# Save results directly to a JSON file
uv run websearch "FastAPI" --json -o results.json

# Specify search engines and Round-Robin rotation strategy
uv run websearch "Generative AI" -e duckduckgo,bing,yahoo -s round_robin

# Bypass cache for fresh live results
uv run websearch "Breaking tech news" --no-cache

# Purge SQLite cache database
uv run websearch --clear-cache

# List available search engines
uv run websearch --list-engines
```

---

## 📐 Architecture & Engine Flow

```mermaid
flowchart TD
    A["User Query (CLI / Python)"] --> B["Normalize Query (Whitespace & Case)"]
    B --> C{"Cache Lookup (Memory / SQLite)"}
    C -- "Cache HIT" --> D["Return Cached SearchResponse (< 1ms)"]
    C -- "Cache MISS" --> E["Engine Rotator (Priority / Round-Robin / Random)"]
    
    E --> F["Attempt Engine #1 (e.g. DuckDuckGo)"]
    F -- "Success" --> G["Parse HTML with BeautifulSoup & Unwrap URLs"]
    F -- "Failure / 429 / 0 Results" --> H["Automatic Fallback Engine #2 (Bing)"]
    
    H -- "Success" --> G
    H -- "Failure" --> I["Fallback Engine #3 (Google / Yahoo / Qwant)"]
    I -- "Success" --> G
    
    G --> J["Store Results in Cache with TTL"]
    J --> K["Return Structured SearchResponse / JSON"]
```

---

## 🔌 Custom Search Engines

Easily create and register custom search providers by inheriting from `BaseSearchEngine`:

```python
from web_search import BaseSearchEngine, EngineRegistry, SearchResult, WebSearcher

class WikipediaSearchEngine(BaseSearchEngine):
    name = "wikipedia"
    display_name = "Wikipedia OpenSearch"

    def search(self, query: str, max_results: int = 10, language: str = "en", region=None) -> list[SearchResult]:
        url = f"https://{language}.wikipedia.org/w/api.php"
        params = {"action": "opensearch", "search": query, "limit": str(max_results), "format": "json"}
        resp = self.session.get(url, params=params, headers=self.get_headers(), timeout=self.timeout)
        data = resp.json()

        titles, snippets, links = data[1], data[2], data[3]
        return [
            SearchResult(
                titre=titles[i],
                url=links[i],
                extrait=snippets[i] if i < len(snippets) else "",
                engine=self.name,
                rank=i + 1,
            )
            for i in range(len(titles))
        ]

# Register engine
EngineRegistry.register("wikipedia", WikipediaSearchEngine)

# Use with automatic fallback to DuckDuckGo
searcher = WebSearcher(engines=["wikipedia", "duckduckgo"])
response = searcher.search("Albert Einstein", max_results=3)
```

---

## 🧪 Testing & Code Quality

Run the complete test suite (55 tests including unit, mock DOM parsing, and live network integration tests):

```bash
# Run test suite
uv run pytest -v

# Run with test coverage report
uv run pytest --cov=web_search --cov-report=term-missing
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

### Engine health and bot challenges

Scraped engines regularly answer with a captcha, an HTTP 202/429, or a "no results" page that is really a block. Since
0.2.0:

- a captcha / "unusual traffic" page is raised as `ChallengeError` (a `RateLimitError`) instead of "no results";
- an engine that hit a block **rests** (5 min, doubling up to 30 min on repeated blocks) and is skipped by the next
  queries, so you stop paying a failed request per query and stop hammering a blocked engine; if every engine is resting
  they are all tried anyway; plain "0 results" never makes an engine rest and a success clears the memory;
- the memory is process-wide by default (`SHARED_HEALTH`), so it also works with the throw-away searchers created by the
  top-level `search()` helper; pass `WebSearcher(health=EngineHealth(cooldown_s=60))` for your own policy;
- `searcher.engine_status()` reports which engines rest, for how long, and why.

