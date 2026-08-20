"""Mojeek independent search engine scraper."""

from __future__ import annotations

import logging
from typing import Optional

from web_search.engines.base import BaseSearchEngine
from web_search.exceptions import EngineError, RateLimitError
from web_search.models import SearchResult

logger = logging.getLogger(__name__)


class MojeekEngine(BaseSearchEngine):
    """Mojeek independent web search engine scraper."""

    name = "mojeek"
    display_name = "Mojeek"

    BASE_URL = "https://www.mojeek.com/search"

    def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
    ) -> list[SearchResult]:
        """Execute search on Mojeek."""
        params = {"q": query}

        headers = self.get_headers()
        headers["Referer"] = "https://www.mojeek.com/"

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=self.timeout,
                proxies=self.proxies,
            )

            if response.status_code == 429:
                raise RateLimitError(self.name, "Mojeek rate limited (HTTP 429)")

            if response.status_code != 200:
                raise EngineError(self.name, f"Mojeek returned HTTP status {response.status_code}")

            results = self._parse_response(response.text, max_results)
            if not results:
                raise EngineError(self.name, f"No results found for query: '{query}'")

            return results[:max_results]

        except (RateLimitError, EngineError):
            raise
        except Exception as e:
            raise EngineError(self.name, f"Mojeek search failed: {e}", original_exception=e)

    def _parse_response(self, html_text: str, max_results: int) -> list[SearchResult]:
        """Parse results from Mojeek HTML."""
        soup = self.parse_html(html_text)
        results: list[SearchResult] = []

        items = soup.select("ul.results-standard > li, .results-standard li")

        for item in items:
            title_elem = item.select_one("a.title, a.ob")
            if not title_elem:
                continue

            title = self.clean_text(title_elem.get_text())
            raw_url = title_elem.get("href")
            clean_link = self.clean_url(raw_url)

            snippet_elem = item.select_one("p.s, p.snippet, p")
            snippet = self.clean_text(snippet_elem.get_text()) if snippet_elem else ""

            if title and clean_link and "mojeek.com" not in clean_link:
                results.append(
                    SearchResult(
                        titre=title,
                        url=clean_link,
                        extrait=snippet,
                        engine=self.name,
                        rank=len(results) + 1,
                    )
                )

            if len(results) >= max_results:
                break

        return results
