"""Google search engine scraper."""

from __future__ import annotations

import logging

from websearch_py.engines.base import BaseSearchEngine
from websearch_py.exceptions import EngineError, RateLimitError
from websearch_py.models import SearchResult

logger = logging.getLogger(__name__)


class GoogleEngine(BaseSearchEngine):
    """Google web search engine scraper."""

    name = "google"
    display_name = "Google"

    BASE_URL = "https://www.google.com/search"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-set consent cookies to bypass EU / international consent walls
        self.session.cookies.set(
            "SOCS",
            "CAISHAgBEhJnd3NfMjAyNDA2MTAtMF9SQzIaAmVuIAEaBgiA_LmvBg",
            domain=".google.com",
        )
        self.session.cookies.set("CONSENT", "YES+cb.20230531-04-p0.en+FX+111", domain=".google.com")
        self.session.cookies.set("1P_JAR", "2024-01-01-00", domain=".google.com")

    def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: str | None = None,
    ) -> list[SearchResult]:
        """Execute search on Google."""
        params = {
            "q": query,
            "num": str(min(max_results + 5, 30)),
            "hl": language or "en",
            "gbv": "1",  # Basic HTML layout flag
        }
        if region:
            params["gl"] = region.lower()

        headers = self.get_headers()
        headers["Referer"] = "https://www.google.com/"

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=self.timeout,
                proxies=self.proxies,
            )

            # Check for bot block / captcha
            if response.status_code == 429 or "sorry/index" in response.url:
                raise RateLimitError(self.name, "Google rate limit or CAPTCHA encountered")

            if response.status_code != 200:
                raise EngineError(self.name, f"Google returned HTTP status {response.status_code}")

            results = self._parse_response(response.text, max_results)
            if not results:
                raise self.empty_result_error(query, response.text)

            return results[:max_results]

        except RateLimitError, EngineError:
            raise
        except Exception as e:
            raise EngineError(self.name, f"Google request failed: {e}", original_exception=e)

    def _parse_response(self, html_text: str, max_results: int) -> list[SearchResult]:
        """Extract search results from Google HTML (supporting multiple DOM structures)."""
        soup = self.parse_html(html_text)
        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        # Strategy 1: Look for containers (Gx5Zad, ZINbbc, g, tF2Cxc, MjjYud)
        containers = soup.select("div.Gx5Zad, div.ZINbbc, div.g, div.tF2Cxc, div.MjjYud, div.kCrYT")

        for container in containers:
            # Find link with href
            a_tag = container.select_one("a[href]")
            if not a_tag:
                continue

            raw_url = a_tag.get("href")
            clean_link = self.clean_url(raw_url)
            if not clean_link or "google.com" in clean_link or clean_link in seen_urls:
                continue

            # Find title
            h3_tag = container.select_one("h3, div.vvjwJb, div.BNeawe.deIvCb")
            title = self.clean_text(h3_tag.get_text() if h3_tag else a_tag.get_text())
            if not title or len(title) < 2:
                continue

            # Find snippet
            snippet_tag = container.select_one(
                "div.VwiC3b, div.BNeawe.s3v9rd.AP7Wnd, div.yXK7lf, span.aCOpRe, div.MUxGbd"
            )
            snippet = ""
            if snippet_tag:
                snippet = self.clean_text(snippet_tag.get_text())
            else:
                # Extract text excluding title
                container_text = self.clean_text(container.get_text())
                if container_text and container_text != title:
                    snippet = container_text.replace(title, "").strip()

            seen_urls.add(clean_link)
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

        # Strategy 2: If strategy 1 found nothing, fallback to parsing all /url?q= links
        if not results:
            for a_tag in soup.find_all("a", href=True):
                raw_url = a_tag["href"]
                clean_link = self.clean_url(raw_url)
                if not clean_link or "google.com" in clean_link or clean_link in seen_urls:
                    continue

                h3 = a_tag.find("h3") or a_tag.find("div")
                title = self.clean_text(h3.get_text() if h3 else a_tag.get_text())
                if not title or len(title) < 2 or title in ["Google", "Images", "Maps", "Actualités", "News"]:
                    continue

                seen_urls.add(clean_link)
                results.append(
                    SearchResult(
                        titre=title,
                        url=clean_link,
                        extrait="",
                        engine=self.name,
                        rank=len(results) + 1,
                    )
                )

                if len(results) >= max_results:
                    break

        return results
