"""Base search engine class with HTTP session, headers rotation, and parsing utilities."""

from __future__ import annotations

import logging
import random
import re
import urllib.parse
from abc import ABC, abstractmethod
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from websearch_py.exceptions import (
    ChallengeError,
    EngineError,
    EngineParseError,
    RateLimitError,
)
from websearch_py.models import SearchResult

logger = logging.getLogger(__name__)

# Modern realistic User-Agents pool
USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    # Safari macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
]


# Phrases found in the <title> / first screen of bot-challenge pages (checked in lower case).
_BLOCK_MARKERS = re.compile(
    r"<title>\s*(captcha|just a moment|attention required|access denied|are you a robot|verify)"
    r"|unusual traffic|automated queries|verify you are (a )?human|are you a robot|robot check|"
    r"complete the (captcha|security check)|detected unusual|enable javascript and cookies to continue|"
    r"g-recaptcha|h-captcha|cf-challenge|/sorry/index",
    re.IGNORECASE,
)


def looks_blocked(html: str) -> bool:
    """True when the page is a bot challenge / captcha rather than a search result page."""
    return bool(html) and bool(_BLOCK_MARKERS.search(html[:6000]))


class BaseSearchEngine(ABC):
    """Abstract base class for all search engines."""

    name: str = "base"
    display_name: str = "Base Engine"

    def __init__(
        self,
        timeout: float = 10.0,
        proxies: Optional[dict[str, str]] = None,
        headers: Optional[dict[str, str]] = None,
        session: Optional[requests.Session] = None,
    ):
        """Initialize engine.

        Args:
            timeout: HTTP request timeout in seconds
            proxies: Optional proxy dict for requests (e.g. {'http': '...', 'https': '...'})
            headers: Optional custom headers to merge
            session: Optional custom requests Session
        """
        self.timeout = timeout
        self.proxies = proxies
        self.custom_headers = headers or {}
        self.session = session or requests.Session()

    def empty_result_error(self, query: str, html: str = "") -> EngineError:
        """Error for a page that gave no result: a ChallengeError when it is a captcha, else a plain EngineError."""
        if looks_blocked(html):
            return ChallengeError(self.name, f"{self.display_name} answered with a bot challenge (captcha)")
        return EngineError(self.name, f"No results found for query: '{query}'")

    def get_headers(self) -> dict[str, str]:
        """Generate realistic browser headers with rotated User-Agent."""
        ua = random.choice(USER_AGENTS)
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        headers.update(self.custom_headers)
        return headers

    def parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse HTML string using lxml if available, falling back to html.parser."""
        try:
            return BeautifulSoup(html_content, "lxml")
        except Exception:
            return BeautifulSoup(html_content, "html.parser")

    def clean_text(self, text: Optional[str]) -> str:
        """Clean and normalize extracted text string."""
        if not text:
            return ""
        # Remove extra whitespace, newlines, tabs
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned

    def clean_url(self, raw_url: Optional[str]) -> Optional[str]:
        """Normalize and unwrap tracking / redirect URLs."""
        if not raw_url:
            return None

        raw_url = raw_url.strip()

        # Handle DuckDuckGo redirect: //duckduckgo.com/l/?uddg=https%3A%2F%2F...
        if "/l/?uddg=" in raw_url or "uddg=" in raw_url:
            match = re.search(r"uddg=([^&]+)", raw_url)
            if match:
                return urllib.parse.unquote(match.group(1))

        # Handle DuckDuckGo ad redirect with target URL in u3=
        if "u3=" in raw_url:
            match = re.search(r"u3=([^&]+)", raw_url)
            if match:
                decoded = urllib.parse.unquote(match.group(1))
                if decoded.startswith("http"):
                    return decoded

        # Handle Google redirect: /url?q=https://...
        if "/url?" in raw_url and "q=" in raw_url:
            parsed = urllib.parse.urlparse(raw_url)
            qs = urllib.parse.parse_qs(parsed.query)
            if "q" in qs and qs["q"][0].startswith("http"):
                return qs["q"][0]

        # Handle Bing redirect: /ck/a?!...&u=a1<base64>
        if "/ck/a?!" in raw_url and "u=" in raw_url:
            import base64
            parsed = urllib.parse.urlparse(raw_url)
            qs = urllib.parse.parse_qs(parsed.query)
            if "u" in qs:
                u_val = qs["u"][0]
                if u_val.startswith("a1"):
                    u_b64 = u_val[2:]
                    u_b64 += "=" * (-len(u_b64) % 4)
                    try:
                        decoded = base64.urlsafe_b64decode(u_b64).decode("utf-8", errors="ignore")
                        if decoded.startswith("http"):
                            return decoded
                    except Exception:
                        pass

        # Handle Yahoo redirect: /RU=https%3a%2f%2f.../RK=2/RS=...
        if "/RU=" in raw_url or "/ru=" in raw_url:
            match = re.search(r"/RU=([^/]+)/", raw_url, re.IGNORECASE)
            if match:
                decoded = urllib.parse.unquote(match.group(1))
                if decoded.startswith("http"):
                    return decoded

        # Ignore non-http links or ads redirects if not resolved
        if raw_url.startswith("//"):
            raw_url = "https:" + raw_url

        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            return raw_url

        return None

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: Optional[str] = None,
    ) -> list[SearchResult]:
        """Execute search query and return list of SearchResult items.

        Raises:
            RateLimitError: If engine returns 429 / CAPTCHA
            EngineParseError: If parsing fails
            EngineError: For general engine / network failures
        """
        pass
