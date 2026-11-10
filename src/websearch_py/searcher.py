"""Main web search orchestrator with fallback, rotation, and cache management."""

from __future__ import annotations

import concurrent.futures
import logging
import time
from collections.abc import Sequence

from websearch_py.cache.base import BaseCache
from websearch_py.cache.memory import InMemoryCache
from websearch_py.cache.null import NullCache
from websearch_py.cache.sqlite import SQLiteCache
from websearch_py.engines.base import BaseSearchEngine
from websearch_py.engines.registry import EngineRegistry
from websearch_py.exceptions import (
    AllEnginesFailedError,
)
from websearch_py.health import SHARED_HEALTH, EngineHealth
from websearch_py.models import (
    RotationStrategy,
    SearchResponse,
)
from websearch_py.rotation import EngineRotator

logger = logging.getLogger(__name__)

# Default engine fallback chain
DEFAULT_ENGINES = [
    "duckduckgo",
    "bing",
    "google",
    "yahoo",
    "qwant",
    "brave",
    "mojeek",
]


class WebSearcher:
    """High-level search coordinator orchestrating engine fallback, rotation, and caching."""

    def __init__(
        self,
        engines: Sequence[str | BaseSearchEngine] | None = None,
        cache: BaseCache | str | bool | None = None,
        strategy: RotationStrategy | str = RotationStrategy.FALLBACK_PRIORITY,
        timeout: float = 10.0,
        cache_ttl: int = 3600,
        proxies: dict[str, str] | None = None,
        health: EngineHealth | None = None,
    ):
        """Initialize WebSearcher.

        Args:
            engines: Sequence of engine names (e.g. ['duckduckgo', 'bing']) or engine instances.
            cache: Cache instance, or True for InMemoryCache, 'sqlite' for SQLiteCache, False/None for NullCache.
            strategy: Engine fallback/rotation strategy (FALLBACK_PRIORITY, ROUND_ROBIN, RANDOM, FASTEST).
            timeout: Default HTTP request timeout per engine in seconds.
            cache_ttl: Default cache TTL in seconds (default: 3600s / 1h).
            proxies: Optional proxy dict for HTTP requests.
            health: Engine health memory (engines that hit a captcha / rate limit rest for a while). Defaults to a
                process-wide instance, so the memory survives the short-lived searchers of the top-level helpers.
        """
        self.health = health or SHARED_HEALTH
        self.timeout = timeout
        self.proxies = proxies

        # 1. Initialize engines
        raw_engines = engines or DEFAULT_ENGINES
        self._engines: list[BaseSearchEngine] = []
        for eng in raw_engines:
            if isinstance(eng, BaseSearchEngine):
                self._engines.append(eng)
            elif isinstance(eng, str):
                self._engines.append(EngineRegistry.create(eng, timeout=timeout, proxies=proxies))
            else:
                raise TypeError(f"Invalid engine type: {type(eng)}")

        if not self._engines:
            raise ValueError("WebSearcher requires at least one search engine.")

        # 2. Initialize rotator
        self.rotator = EngineRotator(self._engines, strategy=strategy)

        # 3. Initialize cache
        if cache is False or cache is None:
            self.cache: BaseCache = NullCache()
        elif cache is True or cache == "memory":
            self.cache = InMemoryCache(default_ttl_seconds=cache_ttl)
        elif cache == "sqlite" or isinstance(cache, str) and cache.endswith(".db"):
            db_path = cache if isinstance(cache, str) and cache.endswith(".db") else "search_cache.db"
            self.cache = SQLiteCache(db_path=db_path, default_ttl_seconds=cache_ttl)
        elif isinstance(cache, BaseCache):
            self.cache = cache
        else:
            # Default to in-memory cache
            self.cache = InMemoryCache(default_ttl_seconds=cache_ttl)

    def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "fr",
        region: str | None = None,
        use_cache: bool = True,
        cache_ttl: int | None = None,
    ) -> SearchResponse:
        """Execute a web search query with caching, rotation, and fallback.

        Args:
            query: The search query string.
            max_results: Maximum number of results to return (default: 10).
            language: Target language code (e.g. 'fr', 'en', default: 'fr').
            region: Optional target region/country code (e.g. 'fr', 'us').
            use_cache: Whether to check and write to cache for this query (default: True).
            cache_ttl: Custom TTL in seconds for this specific query's cache.

        Returns:
            SearchResponse containing results and execution metadata.

        Raises:
            AllEnginesFailedError: If all engines failed or returned no results.
            ValueError: If query is empty.
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty.")

        query_clean = query.strip()
        start_time = time.perf_counter()

        # 1. Check cache for identical query
        if use_cache:
            cached_results = self.cache.get(
                query=query_clean,
                max_results=max_results,
                language=language,
                region=region,
            )
            if cached_results is not None:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                logger.debug(f"Cache HIT for query '{query_clean}' ({len(cached_results)} results)")
                return SearchResponse(
                    query=query_clean,
                    results=cached_results,
                    engine_used="cache",
                    cached=True,
                    execution_time_ms=elapsed_ms,
                    fallback_history=[],
                )

        logger.debug(f"Cache MISS for query '{query_clean}' - proceeding to engines")

        # 2. Strategy FASTEST (concurrent execution)
        if self.rotator.strategy == RotationStrategy.FASTEST:
            response = self._search_fastest(
                query=query_clean,
                max_results=max_results,
                language=language,
                region=region,
                start_time=start_time,
            )
        else:
            # 3. Fallback and Rotation (Sequential attempt in rotator order)
            response = self._search_fallback_rotation(
                query=query_clean,
                max_results=max_results,
                language=language,
                region=region,
                start_time=start_time,
            )

        # 4. Save successful results to cache
        if use_cache and response.results:
            self.cache.set(
                query=query_clean,
                results=response.results,
                max_results=max_results,
                language=language,
                region=region,
                ttl=cache_ttl,
            )

        return response

    def _search_fallback_rotation(
        self,
        query: str,
        max_results: int,
        language: str,
        region: str | None,
        start_time: float,
    ) -> SearchResponse:
        """Attempt engines sequentially according to rotator order."""
        ordered_engines = self.rotator.get_ordered_engines()
        errors: dict[str, str] = {}
        fallback_history: list[str] = []

        # Engines that recently answered with a captcha / rate limit rest, unless every engine is resting.
        healthy = [e for e in ordered_engines if not self.health.is_resting(e.name)]
        for e in ordered_engines:
            if e not in healthy and healthy:
                errors[e.name] = "resting after a recent block (captcha / rate limit)"

        for engine in healthy or ordered_engines:
            fallback_history.append(engine.name)
            logger.info(f"Attempting search with engine '{engine.name}' for '{query}'")

            try:
                results = engine.search(
                    query=query,
                    max_results=max_results,
                    language=language,
                    region=region,
                )

                if results:
                    self.health.record_success(engine.name)
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    logger.info(
                        f"Search SUCCESS with engine '{engine.name}' ({len(results)} results in {elapsed_ms:.1f}ms)"
                    )
                    return SearchResponse(
                        query=query,
                        results=results,
                        engine_used=engine.name,
                        cached=False,
                        execution_time_ms=elapsed_ms,
                        fallback_history=fallback_history,
                    )
                else:
                    errors[engine.name] = "0 results returned"
                    logger.warning(f"Engine '{engine.name}' returned 0 results, falling back...")

            except Exception as e:
                errors[engine.name] = str(e)
                self.health.record_failure(engine.name, e)
                logger.warning(f"Engine '{engine.name}' failed: {e}, falling back to next engine...")

        # If all engines failed
        raise AllEnginesFailedError(query=query, errors=errors)

    def _search_fastest(
        self,
        query: str,
        max_results: int,
        language: str,
        region: str | None,
        start_time: float,
    ) -> SearchResponse:
        """Query all engines concurrently and return the fastest valid response."""
        engines = [e for e in self.rotator.engines if not self.health.is_resting(e.name)] or self.rotator.engines
        errors: dict[str, str] = {}
        fallback_history = [e.name for e in engines]

        def _task(eng: BaseSearchEngine):
            return eng.name, eng.search(
                query=query,
                max_results=max_results,
                language=language,
                region=region,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(engines)) as executor:
            future_to_engine = {executor.submit(_task, eng): eng for eng in engines}

            for future in concurrent.futures.as_completed(future_to_engine):
                engine = future_to_engine[future]
                try:
                    eng_name, results = future.result()
                    if results:
                        self.health.record_success(eng_name)
                        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                        return SearchResponse(
                            query=query,
                            results=results,
                            engine_used=eng_name,
                            cached=False,
                            execution_time_ms=elapsed_ms,
                            fallback_history=fallback_history,
                        )
                    else:
                        errors[engine.name] = "0 results returned"
                except Exception as e:
                    errors[engine.name] = str(e)
                    self.health.record_failure(engine.name, e)

        raise AllEnginesFailedError(query=query, errors=errors)

    def engine_status(self) -> dict[str, dict[str, object]]:
        """Health snapshot: which engines are resting after a block, for how long, and the last error."""
        return self.health.status()

    def search_json(
        self,
        query: str,
        max_results: int = 10,
        language: str = "fr",
        region: str | None = None,
        detailed: bool = False,
        indent: int | None = 2,
        use_cache: bool = True,
        cache_ttl: int | None = None,
    ) -> str:
        """Execute a search and directly output standard JSON string.

        Args:
            query: The search query string.
            max_results: Maximum results to return (default: 10).
            language: Target language (default: 'fr').
            region: Optional target region.
            detailed: If True, include execution metadata (engine, execution_time, etc.).
                      If False (default), output clean JSON list of objects:
                      [{"titre": ..., "url": ..., "extrait": ...}, ...]
            indent: JSON indentation spaces.
            use_cache: Whether to use caching.
            cache_ttl: Cache TTL in seconds.

        Returns:
            Formatted JSON string.
        """
        response = self.search(
            query=query,
            max_results=max_results,
            language=language,
            region=region,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        )
        return response.to_json(detailed=detailed, indent=indent)


# Convenience singleton and top-level functions

_default_searcher: WebSearcher | None = None


def get_default_searcher() -> WebSearcher:
    """Get or initialize default global WebSearcher instance."""
    global _default_searcher
    if _default_searcher is None:
        _default_searcher = WebSearcher(cache=True)
    return _default_searcher


def search(
    query: str,
    max_results: int = 10,
    language: str = "fr",
    region: str | None = None,
    use_cache: bool = True,
    strategy: RotationStrategy | str = RotationStrategy.FALLBACK_PRIORITY,
    engines: Sequence[str | BaseSearchEngine] | None = None,
) -> SearchResponse:
    """Top-level convenience search function.

    Args:
        query: Search query text
        max_results: Maximum items to return (default: 10)
        language: Language code (default: 'fr')
        region: Country code (e.g. 'fr', 'us')
        use_cache: Cache identical queries (default: True)
        strategy: Engine rotation strategy (default: FALLBACK_PRIORITY)
        engines: Optional list of engines to use

    Returns:
        SearchResponse with .results, .engine_used, .cached, .execution_time_ms
    """
    if engines is not None or strategy != RotationStrategy.FALLBACK_PRIORITY:
        searcher = WebSearcher(engines=engines, strategy=strategy, cache=use_cache)
        return searcher.search(
            query=query,
            max_results=max_results,
            language=language,
            region=region,
            use_cache=use_cache,
        )

    searcher = get_default_searcher()
    return searcher.search(
        query=query,
        max_results=max_results,
        language=language,
        region=region,
        use_cache=use_cache,
    )


def search_json(
    query: str,
    max_results: int = 10,
    language: str = "fr",
    region: str | None = None,
    detailed: bool = False,
    indent: int | None = 2,
    use_cache: bool = True,
    strategy: RotationStrategy | str = RotationStrategy.FALLBACK_PRIORITY,
    engines: Sequence[str | BaseSearchEngine] | None = None,
) -> str:
    """Top-level convenience search function outputting JSON string with titre, url, extrait.

    Args:
        query: Search query text
        max_results: Maximum items to return (default: 10)
        language: Language code (default: 'fr')
        region: Country code
        detailed: If True, output full metadata; if False, output clean result items list
        indent: JSON indentation (default: 2)
        use_cache: Cache identical queries (default: True)
        strategy: Engine rotation strategy
        engines: Optional list of engines to use

    Returns:
        JSON formatted string.
    """
    resp = search(
        query=query,
        max_results=max_results,
        language=language,
        region=region,
        use_cache=use_cache,
        strategy=strategy,
        engines=engines,
    )
    return resp.to_json(detailed=detailed, indent=indent)
