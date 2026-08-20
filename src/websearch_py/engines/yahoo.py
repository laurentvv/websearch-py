"""Yahoo search engine scraper."""

from __future__ import annotations

import logging
from typing import Optional

from websearch_py.engines.base import BaseSearchEngine
from websearch_py.exceptions import EngineError, RateLimitError
from websearch_py.models import SearchResult

logger = logging.getLogger(__name__)


class YahooEngine(BaseSearchEngine):
    """Yahoo web search engine scraper."""

    name = "yahoo"
    display_name = "Yahoo"

    BASE_URL = "https://search.yahoo.com/search"

    def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
    ) -> list[SearchResult]:
        """Execute search on Yahoo."""
        params = {
            "p": query,
            "n": str(min(max_results + 5, 30)),
            "ei": "UTF-8",
        }
        if language:
            params["vl"] = f"lang_{language}"

        headers = self.get_headers()
        headers["Referer"] = "https://search.yahoo.com/"

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=self.timeout,
                proxies=self.proxies,
            )

            if response.status_code == 429:
                raise RateLimitError(self.name, "Yahoo rate limit encountered (HTTP 429)")

            if response.status_code != 200:
                raise EngineError(self.name, f"Yahoo returned HTTP status {response.status_code}")

            results = self._parse_response(response.text, max_results)
            if not results:
                raise EngineError(self.name, f"No results found for query: '{query}'")

            return results[:max_results]

        except (RateLimitError, EngineError):
            raise
        except Exception as e:
            raise EngineError(self.name, f"Yahoo request failed: {e}", original_exception=e)

    def _parse_response(self, html_text: str, max_results: int) -> list[SearchResult]:
        """Parse search results from Yahoo HTML."""
        soup = self.parse_html(html_text)
        results: list[SearchResult] = []

        items = soup.select("div.algo, div.dd.algo, li.algo, div.Sr")

        for item in items:
            title_elem = item.select_one("h3.title a, a.d-ib, h3 a, h4.title a")
            if not title_elem:
                continue

            title = self.clean_text(title_elem.get_text())
            raw_url = title_elem.get("href")
            clean_link = self.clean_url(raw_url)

            snippet_elem = item.select_one("div.compText, div.algo-desc, p.lh-16, p")
            snippet = self.clean_text(snippet_elem.get_text()) if snippet_elem else ""

            if title and clean_link and "search.yahoo.com" not in clean_link:
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
