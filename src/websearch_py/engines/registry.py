"""Engine registry for creating and managing search engine instances."""

from __future__ import annotations

from typing import ClassVar

import requests

from websearch_py.engines.base import BaseSearchEngine
from websearch_py.engines.bing import BingEngine
from websearch_py.engines.brave import BraveEngine
from websearch_py.engines.duckduckgo import DuckDuckGoEngine, DuckDuckGoLiteEngine
from websearch_py.engines.google import GoogleEngine
from websearch_py.engines.mojeek import MojeekEngine
from websearch_py.engines.qwant import QwantEngine
from websearch_py.engines.yahoo import YahooEngine
from websearch_py.exceptions import WebSearchError


class EngineRegistry:
    """Registry mapping engine identifiers to engine classes."""

    _ENGINES: ClassVar[dict[str, type[BaseSearchEngine]]] = {
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
    def register(cls, name: str, engine_cls: type[BaseSearchEngine]) -> None:
        """Register a new custom search engine class."""
        cls._ENGINES[name.lower().strip()] = engine_cls

    @classmethod
    def get(cls, name: str) -> type[BaseSearchEngine]:
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
        proxies: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        session: requests.Session | None = None,
    ) -> BaseSearchEngine:
        """Instantiate an engine by name."""
        engine_cls = cls.get(name)
        return engine_cls(
            timeout=timeout,
            proxies=proxies,
            headers=headers,
            session=session,
        )
