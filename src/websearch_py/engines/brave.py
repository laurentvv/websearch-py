"""Brave Search engine scraper."""

from __future__ import annotations

import logging
from typing import Optional

from websearch_py.engines.base import BaseSearchEngine
from websearch_py.exceptions import EngineError, RateLimitError
from websearch_py.models import SearchResult

logger = logging.getLogger(__name__)


class BraveEngine(BaseSearchEngine):
    """Brave web search engine scraper."""

    name = "brave"
    display_name = "Brave Search"

    BASE_URL = "https://search.brave.com/search"

    def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
    ) -> list[SearchResult]:
        """Execute search on Brave Search."""
        params = {"q": query, "source": "web"}
        if country := region:
            params["country"] = country.lower()

        headers = self.get_headers()
        headers["Referer"] = "https://search.brave.com/"

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=self.timeout,
                proxies=self.proxies,
            )

            if response.status_code == 429:
                raise RateLimitError(self.name, "Brave Search rate limit encountered (HTTP 429)")

            if response.status_code != 200:
                raise EngineError(self.name, f"Brave returned HTTP status {response.status_code}")

            results = self._parse_response(response.text, max_results)
            if not results:
                raise self.empty_result_error(query, response.text)

            return results[:max_results]

        except (RateLimitError, EngineError):
            raise
        except Exception as e:
            raise EngineError(self.name, f"Brave search failed: {e}", original_exception=e)

    def _parse_response(self, html_text: str, max_results: int) -> list[SearchResult]:
        """Parse search results from Brave Search HTML."""
        soup = self.parse_html(html_text)
        results: list[SearchResult] = []

        items = soup.select('div.snippet[data-type="web"], div.snippet, div.result')

        for item in items:
            title_elem = item.select_one(".title, a.heading, .snippet-title, h3")
            link_elem = item.select_one("a[href]")
            if not title_elem or not link_elem:
                continue

            title = self.clean_text(title_elem.get_text())
            raw_url = link_elem.get("href")
            clean_link = self.clean_url(raw_url)

            snippet_elem = item.select_one(
                ".snippet-description, .snippet-content, div.generic-snippet, p"
            )
            snippet = self.clean_text(snippet_elem.get_text()) if snippet_elem else ""

            if title and clean_link and "search.brave.com" not in clean_link:
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
