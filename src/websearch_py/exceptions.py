"""Custom exceptions for the web search library."""


class WebSearchError(Exception):
    """Base exception for all web search errors."""


class EngineError(WebSearchError):
    """Raised when a specific search engine fails to execute a search."""

    def __init__(self, engine_name: str, message: str, original_exception: Exception | None = None):
        self.engine_name = engine_name
        self.original_exception = original_exception
        super().__init__(f"[{engine_name}] {message}")


class RateLimitError(EngineError):
    """Raised when an engine returns HTTP 429 or CAPTCHA block."""


class ChallengeError(RateLimitError):
    """The engine answered with a bot challenge (captcha, "unusual traffic"...) instead of results."""


class EngineParseError(EngineError):
    """Raised when HTML parsing fails to extract search results."""


class AllEnginesFailedError(WebSearchError):
    """Raised when all configured search engines have failed or returned no results."""

    def __init__(self, query: str, errors: dict[str, str]):
        self.query = query
        self.errors = errors
        error_summary = "; ".join(f"{eng}: {err}" for eng, err in errors.items())
        super().__init__(f"All engines failed for query '{query}'. Errors: {error_summary}")


class CacheError(WebSearchError):
    """Raised when a cache backend encounters an error."""
