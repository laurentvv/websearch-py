"""Web search package with Fallback, Rotation, and Cache management.

Supports DuckDuckGo, Bing, Google, Yahoo, Qwant, Brave, Mojeek, etc.
Outputs structured JSON with `titre`, `url`, `extrait`.
"""

from websearch_py.cache.base import BaseCache, normalize_query
from websearch_py.cache.memory import InMemoryCache
from websearch_py.cache.null import NullCache
from websearch_py.cache.sqlite import SQLiteCache
from websearch_py.engines.base import BaseSearchEngine
from websearch_py.engines.bing import BingEngine
from websearch_py.engines.brave import BraveEngine
from websearch_py.engines.duckduckgo import DuckDuckGoEngine, DuckDuckGoLiteEngine
from websearch_py.engines.google import GoogleEngine
from websearch_py.engines.mojeek import MojeekEngine
from websearch_py.engines.qwant import QwantEngine
from websearch_py.engines.registry import EngineRegistry
from websearch_py.engines.yahoo import YahooEngine
from websearch_py.exceptions import (
    AllEnginesFailedError,
    ChallengeError,
    CacheError,
    EngineError,
    EngineParseError,
    RateLimitError,
    WebSearchError,
)
from websearch_py.health import SHARED_HEALTH, EngineHealth
from websearch_py.models import (
    EngineName,
    RotationStrategy,
    SearchResponse,
    SearchResult,
)
from websearch_py.rotation import EngineRotator
from websearch_py.searcher import (
    WebSearcher,
    get_default_searcher,
    search,
    search_json,
)

__version__ = "0.2.0"

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
    "ChallengeError",
    "EngineHealth",
    "SHARED_HEALTH",
    "CacheError",
]
