"""DuckDuckGo search engine scraper (HTML and Lite endpoints)."""

from __future__ import annotations

import logging

from websearch_py.engines.base import BaseSearchEngine
from websearch_py.exceptions import EngineError, RateLimitError
from websearch_py.models import SearchResult

logger = logging.getLogger(__name__)


class DuckDuckGoEngine(BaseSearchEngine):
    """DuckDuckGo web search scraper using HTML and Lite endpoints."""

    name = "duckduckgo"
    display_name = "DuckDuckGo"

    HTML_URL = "https://html.duckduckgo.com/html/"
    LITE_URL = "https://lite.duckduckgo.com/lite/"

    def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: str | None = None,
    ) -> list[SearchResult]:
        """Execute search on DuckDuckGo."""
        results: list[SearchResult] = []

        # Region format for DuckDuckGo: wt-wt (worldwide), fr-fr, us-en, etc.
        kl = "wt-wt"
        if region:
            kl = f"{region.lower()}-{language.lower()}" if language else f"{region.lower()}-{region.lower()}"
        elif language:
            kl = f"{language.lower()}-{language.lower()}"

        payload = {
            "q": query,
            "kl": kl,
            "b": "",
        }

        headers = self.get_headers()
        headers["Origin"] = "https://html.duckduckgo.com"
        headers["Referer"] = "https://html.duckduckgo.com/"

        # 1. Try DuckDuckGo HTML endpoint (POST then GET)
        try:
            response = self.session.post(
                self.HTML_URL,
                data=payload,
                headers=headers,
                timeout=self.timeout,
                proxies=self.proxies,
            )
            if response.status_code in (202, 403, 429):
                raise RateLimitError(self.name, f"DuckDuckGo rate limit or challenge (HTTP {response.status_code})")

            if response.status_code == 200:
                results = self._parse_html_response(response.text, max_results)

            if not results:
                # Try GET on HTML_URL
                resp_get = self.session.get(
                    self.HTML_URL,
                    params={"q": query, "kl": kl},
                    headers=headers,
                    timeout=self.timeout,
                    proxies=self.proxies,
                )
                if resp_get.status_code in (202, 403, 429):
                    raise RateLimitError(self.name, f"DuckDuckGo GET challenge (HTTP {resp_get.status_code})")
                if resp_get.status_code == 200:
                    results = self._parse_html_response(resp_get.text, max_results)
        except RateLimitError:
            raise
        except Exception as e:
            logger.warning(f"DuckDuckGo HTML endpoint error: {e}, falling back to Lite endpoint")

        # 2. Fallback to DuckDuckGo Lite endpoint (POST then GET)
        if not results:
            try:
                headers_lite = self.get_headers()
                headers_lite["Origin"] = "https://lite.duckduckgo.com"
                headers_lite["Referer"] = "https://lite.duckduckgo.com/"
                response_lite = self.session.post(
                    self.LITE_URL,
                    data=payload,
                    headers=headers_lite,
                    timeout=self.timeout,
                    proxies=self.proxies,
                )
                if response_lite.status_code in (202, 403, 429):
                    raise RateLimitError(
                        self.name, f"DuckDuckGo Lite rate limit or challenge (HTTP {response_lite.status_code})"
                    )

                if response_lite.status_code == 200:
                    results = self._parse_lite_response(response_lite.text, max_results)

                if not results:
                    resp_lite_get = self.session.get(
                        self.LITE_URL,
                        params={"q": query, "kl": kl},
                        headers=headers_lite,
                        timeout=self.timeout,
                        proxies=self.proxies,
                    )
                    if resp_lite_get.status_code in (202, 403, 429):
                        raise RateLimitError(
                            self.name, f"DuckDuckGo Lite GET challenge (HTTP {resp_lite_get.status_code})"
                        )
                    if resp_lite_get.status_code == 200:
                        results = self._parse_lite_response(resp_lite_get.text, max_results)
            except RateLimitError:
                raise
            except Exception as e:
                logger.warning(f"DuckDuckGo Lite endpoint error: {e}")

        if not results:
            raise EngineError(self.name, f"No results found for query: '{query}'")

        return results[:max_results]

    def _parse_html_response(self, html_text: str, max_results: int) -> list[SearchResult]:
        """Parse standard DuckDuckGo HTML page."""
        soup = self.parse_html(html_text)
        results: list[SearchResult] = []
        result_elements = soup.select(".result.results_links, .result, .web-result")

        for el in result_elements:
            # Skip ad results or empty elements
            if "result--ad" in el.get("class", []):
                continue

            title_elem = el.select_one(".result__title a, .result__a, a.result__url")
            snippet_elem = el.select_one(".result__snippet")

            if not title_elem:
                continue

            title = self.clean_text(title_elem.get_text())
            raw_url = title_elem.get("href")
            clean_link = self.clean_url(raw_url)
            snippet = self.clean_text(snippet_elem.get_text()) if snippet_elem else ""

            # Validate result
            if title and clean_link and "duckduckgo.com" not in clean_link:
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

    def _parse_lite_response(self, html_text: str, max_results: int) -> list[SearchResult]:
        """Parse DuckDuckGo Lite table page."""
        soup = self.parse_html(html_text)
        results: list[SearchResult] = []

        links = soup.select("a.result-link")
        snippets = soup.select("td.result-snippet")

        for i, link_elem in enumerate(links):
            title = self.clean_text(link_elem.get_text())
            raw_url = link_elem.get("href")
            clean_link = self.clean_url(raw_url)

            snippet = ""
            if i < len(snippets):
                snippet = self.clean_text(snippets[i].get_text())

            if title and clean_link and "duckduckgo.com" not in clean_link:
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


class DuckDuckGoLiteEngine(DuckDuckGoEngine):
    """DuckDuckGo search specifically using the lightweight Lite endpoint."""

    name = "duckduckgo_lite"
    display_name = "DuckDuckGo Lite"

    def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: str | None = None,
    ) -> list[SearchResult]:
        payload = {"q": query, "kl": "wt-wt", "b": ""}
        headers = self.get_headers()
        headers["Origin"] = "https://lite.duckduckgo.com"
        headers["Referer"] = "https://lite.duckduckgo.com/"

        try:
            resp = self.session.post(
                self.LITE_URL,
                data=payload,
                headers=headers,
                timeout=self.timeout,
                proxies=self.proxies,
            )
            if resp.status_code == 429:
                raise RateLimitError(self.name, "DuckDuckGo Lite rate limited")
            if resp.status_code != 200:
                raise EngineError(self.name, f"HTTP status {resp.status_code}")

            results = self._parse_lite_response(resp.text, max_results)
            if not results:
                raise EngineError(self.name, f"No results found for query '{query}'")
            return results
        except RateLimitError, EngineError:
            raise
        except Exception as e:
            raise EngineError(self.name, f"Request failed: {e}", original_exception=e)
