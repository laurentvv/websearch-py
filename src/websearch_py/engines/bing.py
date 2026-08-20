"""Bing search engine scraper."""

from __future__ import annotations

import logging
import urllib.parse
from typing import Optional

from websearch_py.engines.base import BaseSearchEngine
from websearch_py.exceptions import EngineError, RateLimitError
from websearch_py.models import SearchResult

logger = logging.getLogger(__name__)


class BingEngine(BaseSearchEngine):
    """Bing web search engine scraper."""

    name = "bing"
    display_name = "Bing"

    BASE_URL = "https://www.bing.com/search"

    def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
    ) -> list[SearchResult]:
        """Execute search on Bing."""
        params = {
            "q": query,
            "count": str(min(max_results + 5, 50)),
        }
        if language:
            params["setlang"] = language
        if region:
            params["cc"] = region.upper()

        headers = self.get_headers()
        headers["Referer"] = "https://www.bing.com/"

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=self.timeout,
                proxies=self.proxies,
            )

            if response.status_code == 429:
                raise RateLimitError(self.name, "Bing rate limit encountered (HTTP 429)")

            if response.status_code != 200:
                raise EngineError(self.name, f"Bing returned HTTP status {response.status_code}")

            results = self._parse_response(response.text, max_results)
            if not results:
                raise EngineError(self.name, f"No results found for query: '{query}'")

            return results[:max_results]

        except (RateLimitError, EngineError):
            raise
        except Exception as e:
            raise EngineError(self.name, f"Bing request failed: {e}", original_exception=e)

    def _parse_response(self, html_text: str, max_results: int) -> list[SearchResult]:
        """Parse Bing search results from HTML."""
        soup = self.parse_html(html_text)
        results: list[SearchResult] = []

        # Find search result items
        items = soup.select("li.b_algo, div.b_algo")

        for item in items:
            title_elem = item.select_one("h2 a, h3 a, a.b_title")
            if not title_elem:
                continue

            title = self.clean_text(title_elem.get_text())
            raw_url = title_elem.get("href")
            clean_link = self.clean_url(raw_url)

            # Find snippet
            snippet_elem = item.select_one(
                ".b_caption p, .b_algoSlug, .b_snippet, .b_lineclamp2, .b_lineclamp3, .b_paract"
            )
            snippet = self.clean_text(snippet_elem.get_text()) if snippet_elem else ""

            # Check if this is an algorithmic result (skip internal bing tools / ads)
            if title and clean_link and "bing.com" not in clean_link and "microsoft.com/en-us/bing" not in clean_link:
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
