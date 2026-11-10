"""Qwant search engine scraper."""

from __future__ import annotations

import logging

from websearch_py.engines.base import BaseSearchEngine
from websearch_py.exceptions import EngineError, RateLimitError
from websearch_py.models import SearchResult

logger = logging.getLogger(__name__)


class QwantEngine(BaseSearchEngine):
    """Qwant web search engine scraper."""

    name = "qwant"
    display_name = "Qwant"

    API_URL = "https://api.qwant.com/v3/search/web"
    LITE_URL = "https://lite.qwant.com/"

    def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: str | None = None,
    ) -> list[SearchResult]:
        """Execute search on Qwant."""
        results: list[SearchResult] = []
        locale = f"{language.lower()}_{language.upper()}" if language else "fr_FR"
        if region:
            locale = f"{language.lower()}_{region.upper()}"

        headers = self.get_headers()
        headers["Referer"] = "https://www.qwant.com/"

        # 1. Try Qwant API endpoint
        try:
            params = {
                "q": query,
                "count": str(max_results),
                "locale": locale,
                "safesearch": "1",
            }
            resp = self.session.get(
                self.API_URL,
                params=params,
                headers=headers,
                timeout=self.timeout,
                proxies=self.proxies,
            )
            if resp.status_code == 429:
                raise RateLimitError(self.name, "Qwant rate limited")
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", {}).get("result", {}).get("items", {}).get("mainline", [])
                for group in items:
                    for item in group.get("items", []):
                        title = self.clean_text(item.get("title"))
                        link = self.clean_url(item.get("url"))
                        snippet = self.clean_text(item.get("desc"))
                        if title and link:
                            results.append(
                                SearchResult(
                                    titre=title,
                                    url=link,
                                    extrait=snippet,
                                    engine=self.name,
                                    rank=len(results) + 1,
                                )
                            )
                        if len(results) >= max_results:
                            break
        except RateLimitError:
            raise
        except Exception as e:
            logger.debug(f"Qwant API error: {e}, attempting lite HTML fallback")

        # 2. Try Qwant Lite HTML fallback if API failed or returned 0 results
        if not results:
            try:
                params_lite = {"q": query, "t": "web"}
                resp_lite = self.session.get(
                    self.LITE_URL,
                    params=params_lite,
                    headers=headers,
                    timeout=self.timeout,
                    proxies=self.proxies,
                )
                if resp_lite.status_code == 200:
                    soup = self.parse_html(resp_lite.text)
                    for item in soup.select("article, .result, div.result"):
                        title_el = item.select_one("h2 a, a.title, a")
                        snippet_el = item.select_one("p.desc, p")
                        if title_el:
                            title = self.clean_text(title_el.get_text())
                            link = self.clean_url(title_el.get("href"))
                            snippet = self.clean_text(snippet_el.get_text()) if snippet_el else ""
                            if title and link:
                                results.append(
                                    SearchResult(
                                        titre=title,
                                        url=link,
                                        extrait=snippet,
                                        engine=self.name,
                                        rank=len(results) + 1,
                                    )
                                )
                        if len(results) >= max_results:
                            break
            except Exception as e:
                logger.debug(f"Qwant Lite error: {e}")

        if not results:
            raise EngineError(self.name, f"No results found for query: '{query}'")

        return results[:max_results]
