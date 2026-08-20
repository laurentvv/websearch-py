"""Web search package with Fallback, Rotation, and Cache management.

Supports DuckDuckGo, Bing, Google, Yahoo, Qwant, Brave, Mojeek, etc.
Outputs structured JSON with `titre`, `url`, `extrait`.
"""

from web_search.cache.base import BaseCache, normalize_query
from web_search.cache.memory import InMemoryCache
from web_search.cache.null import NullCache
from web_search.cache.sqlite import SQLiteCache
from web_search.engines.base import BaseSearchEngine
from web_search.engines.bing import BingEngine
from web_search.engines.brave import BraveEngine
from web_search.engines.duckduckgo import DuckDuckGoEngine, DuckDuckGoLiteEngine
from web_search.engines.google import GoogleEngine
from web_search.engines.mojeek import MojeekEngine
from web_search.engines.qwant import QwantEngine
from web_search.engines.registry import EngineRegistry
from web_search.engines.yahoo import YahooEngine
from web_search.exceptions import (
    AllEnginesFailedError,
    CacheError,
    EngineError,
    EngineParseError,
    RateLimitError,
    WebSearchError,
)
from web_search.models import (
    EngineName,
    RotationStrategy,
    SearchResponse,
    SearchResult,
)
from web_search.rotation import EngineRotator
from web_search.searcher import (
    WebSearcher,
    get_default_searcher,
    search,
    search_json,
)

__version__ = "0.1.0"

__all__ = [
    # Top-level API
    "search",
    "search_json",
    "WebSearcher",
    "get_default_searcher",
    # Models
    "SearchResult",
    "SearchResponse",
    "RotationStrategy",
    "EngineName",
    # Cache
    "BaseCache",
    "InMemoryCache",
    "SQLiteCache",
    "NullCache",
    "normalize_query",
    # Engines
    "BaseSearchEngine",
    "DuckDuckGoEngine",
    "DuckDuckGoLiteEngine",
    "BingEngine",
    "GoogleEngine",
    "YahooEngine",
    "QwantEngine",
    "BraveEngine",
    "MojeekEngine",
    "EngineRegistry",
    # Rotation
    "EngineRotator",
    # Exceptions
    "WebSearchError",
    "EngineError",
    "RateLimitError",
    "EngineParseError",
    "AllEnginesFailedError",
    "CacheError",
]
