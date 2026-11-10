"""Base search engine class with HTTP session, headers rotation, and parsing utilities."""

from __future__ import annotations

import logging
import random
import re
import urllib.parse
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString

from websearch_py.exceptions import (
    ChallengeError,
    EngineError,
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


# --- bot-challenge detection ---------------------------------------------------------------------------------------
# A challenge page is recognised from its own structure, never from words that a result snippet or an echoed query
# may contain ("captcha", "unusual traffic"...). Three signals, any of them is enough:
#   1. names in its markup: class / id of an element, path of a form action, of a script / iframe source or of a
#      meta refresh (reCAPTCHA, hCaptcha, ALTCHA, Cloudflare, DuckDuckGo anomaly modal, Google "sorry" / "enablejs");
#   2. its <title>, when the whole title is a challenge title ("Captcha", "Just a moment...");
#   3. a challenge sentence in the lead of the page: the visible text placed before the first text link. A challenge
#      page opens with its message, a result page opens with links.
_MARKUP_MARKERS = re.compile(
    r"captcha|altcha|challenge|anomaly-modal|anomaly\.js|cf-turnstile|/sorry/index|/httpservice/retry/enablejs",
    re.IGNORECASE,
)
_CHALLENGE_TITLE = re.compile(
    r"(captcha|just a moment|attention required|access denied|are you a robot|robot check|security check|"
    r"verification required|human verification|verify (that )?you are (a )?human)\W*",
    re.IGNORECASE,
)
_CHALLENGE_PHRASES = re.compile(
    r"unusual traffic|automated (queries|requests)|verify (that )?you are (a |not a )?(human|robot)|are you a robot|"
    r"robot check|complete the (following )?(captcha|challenge|security check)|flagged as (being )?suspicious|"
    r"bots use duckduckgo|enable javascript and cookies to continue|required to complete this challenge",
    re.IGNORECASE,
)
# Site suffix of a title: "Captcha - Brave Search", "Attention Required! | Cloudflare".
_TITLE_SITE_SUFFIX = re.compile(r"\s+[-|–—·]\s+")


def _parse(html: str) -> BeautifulSoup:
    """Parse HTML with lxml when available, else with the standard library parser."""
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _has_challenge_markup(soup: BeautifulSoup) -> bool:
    for tag in soup.find_all(True):
        names = [*(tag.get("class") or []), tag.get("id") or ""]
        target = ""
        if tag.name == "form":
            target = tag.get("action") or ""
        elif tag.name in ("script", "iframe"):
            target = tag.get("src") or ""
        elif tag.name == "meta" and (tag.get("http-equiv") or "").lower() == "refresh":
            target = tag.get("content") or ""
        names.append(str(target).split("?", 1)[0])  # the query string may echo the user's query
        if any(_MARKUP_MARKERS.search(str(name)) for name in names):
            return True
    return False


def _lead_text(soup: BeautifulSoup) -> str:
    """Visible text placed before the first text link of the page."""
    for tag in soup(["script", "style", "template"]):
        tag.decompose()
    root = soup.body or soup
    first_link = next((a for a in root.find_all("a", href=True) if a.get_text(strip=True)), None)
    parts: list[str] = []
    for node in root.descendants:
        if node is first_link:
            break
        if type(node) is NavigableString:  # not Comment / Doctype / CData
            parts.append(str(node))
    return _squash(" ".join(parts))


def looks_blocked(html: str, query: str = "") -> bool:
    """True when the page is a bot challenge / captcha rather than a search result (or "no result") page.

    Args:
        html: The page to inspect.
        query: The query that produced the page, when known: its echo (page title, "No results for ...") is ignored.
    """
    if not html or not html.strip():
        return False
    soup = _parse(html)
    if _has_challenge_markup(soup):
        return True

    query = _squash(query).lower()
    title = _squash(soup.title.get_text()) if soup.title else ""
    echoes_query = bool(query) and title.lower().startswith(query)
    if title and not echoes_query and _CHALLENGE_TITLE.fullmatch(_TITLE_SITE_SUFFIX.split(title, maxsplit=1)[0]):
        return True

    lead = _lead_text(soup)
    if query:
        lead = re.sub(re.escape(query), " ", lead, flags=re.IGNORECASE)
    return bool(_CHALLENGE_PHRASES.search(lead))


class BaseSearchEngine(ABC):
    """Abstract base class for all search engines."""

    name: str = "base"
    display_name: str = "Base Engine"

    def __init__(
        self,
        timeout: float = 10.0,
        proxies: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        session: requests.Session | None = None,
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

    def empty_result_error(self, query: str, *pages: str) -> EngineError:
        """Error for an answer without results.

        A ChallengeError when one of the answered pages is a bot challenge (the engine then rests), else the plain
        "no results" EngineError, which never makes an engine rest.
        """
        if any(looks_blocked(page, query) for page in pages):
            return ChallengeError(self.name, f"{self.display_name} answered with a bot challenge instead of results")
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
        return _parse(html_content)

    def clean_text(self, text: str | None) -> str:
        """Clean and normalize extracted text string."""
        if not text:
            return ""
        # Remove extra whitespace, newlines, tabs
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned

    def clean_url(self, raw_url: str | None) -> str | None:
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
                    except Exception:  # noqa: S110 - not a base64 redirect: fall through to the plain URL checks
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

        if raw_url.startswith(("http://", "https://")):
            return raw_url

        return None

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        region: str | None = None,
    ) -> list[SearchResult]:
        """Execute search query and return list of SearchResult items.

        Raises:
            RateLimitError: If engine returns 429 / CAPTCHA
            EngineParseError: If parsing fails
            EngineError: For general engine / network failures
        """
