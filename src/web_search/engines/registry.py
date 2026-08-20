"""Engine registry for creating and managing search engine instances."""

from __future__ import annotations

from typing import Any, Optional, Type

import requests

from web_search.engines.base import BaseSearchEngine
from web_search.engines.bing import BingEngine
from web_search.engines.brave import BraveEngine
from web_search.engines.duckduckgo import DuckDuckGoEngine, DuckDuckGoLiteEngine
from web_search.engines.google import GoogleEngine
from web_search.engines.mojeek import MojeekEngine
from web_search.engines.qwant import QwantEngine
from web_search.engines.yahoo import YahooEngine
from web_search.exceptions import WebSearchError


class EngineRegistry:
    """Registry mapping engine identifiers to engine classes."""

    _ENGINES: dict[str, Type[BaseSearchEngine]] = {
        "duckduckgo": DuckDuckGoEngine,
        "ddg": DuckDuckGoEngine,
        "duckduckgo_lite": DuckDuckGoLiteEngine,
        "ddg_lite": DuckDuckGoLiteEngine,
        "bing": BingEngine,
        "google": GoogleEngine,
        "yahoo": YahooEngine,
        "qwant": QwantEngine,
        "brave": BraveEngine,
        "mojeek": MojeekEngine,
    }

    @classmethod
    def register(cls, name: str, engine_cls: Type[BaseSearchEngine]) -> None:
        """Register a new custom search engine class."""
        cls._ENGINES[name.lower().strip()] = engine_cls

    @classmethod
    def get(cls, name: str) -> Type[BaseSearchEngine]:
        """Get engine class by name or alias."""
        key = name.lower().strip()
        if key not in cls._ENGINES:
            available = ", ".join(sorted(set(cls._ENGINES.keys())))
            raise WebSearchError(f"Unknown search engine '{name}'. Available: {available}")
        return cls._ENGINES[key]

    @classmethod
    def list_available(cls) -> list[str]:
        """List distinct engine names."""
        distinct = {cls._ENGINES[k].name for k in cls._ENGINES}
        return sorted(distinct)

    @classmethod
    def create(
        cls,
        name: str,
        timeout: float = 10.0,
        proxies: Optional[dict[str, str]] = None,
        headers: Optional[dict[str, str]] = None,
        session: Optional[requests.Session] = None,
    ) -> BaseSearchEngine:
        """Instantiate an engine by name."""
        engine_cls = cls.get(name)
        return engine_cls(
            timeout=timeout,
            proxies=proxies,
            headers=headers,
            session=session,
        )
