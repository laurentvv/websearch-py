"""Challenge-page detection and engine health memory (cooldown after a captcha / rate limit)."""

import pytest

from websearch_py import ChallengeError, EngineHealth, RateLimitError, WebSearcher
from websearch_py.engines.base import BaseSearchEngine, looks_blocked
from websearch_py.engines.mojeek import MojeekEngine
from websearch_py.exceptions import AllEnginesFailedError, EngineError
from websearch_py.models import RotationStrategy, SearchResult

CAPTCHA_PAGE = "<html><head><title>Captcha</title></head><body><p>Please verify you are human</p></body></html>"
GOOGLE_SORRY = "<html><body>Our systems have detected unusual traffic from your computer network.</body></html>"
OK_PAGE = "<html><head><title>php2shell - Search</title></head><body><ul class='results-standard'></ul></body></html>"


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class ScriptedEngine(BaseSearchEngine):
    """Engine whose behaviour is a list of outcomes: an exception to raise, [] for no results, or a result list."""

    def __init__(self, name, outcomes):
        super().__init__()
        self.name, self.display_name, self.outcomes, self.calls = name, name, list(outcomes), 0

    def search(self, query, max_results=10, language="en", region=None):
        self.calls += 1
        outcome = self.outcomes[min(self.calls - 1, len(self.outcomes) - 1)]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def hit(engine):
    return [SearchResult(titre="t", url="https://example.org", extrait="s", engine=engine, rank=1)]


# --- challenge detection ------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "html",
    [CAPTCHA_PAGE, GOOGLE_SORRY, "<title>Just a moment...</title>", '<div class="g-recaptcha" data-sitekey="k"></div>'],
)
def test_challenge_pages_are_recognised(html):
    assert looks_blocked(html)


@pytest.mark.parametrize(
    "html",
    [
        OK_PAGE,
        "",
        "<html><body>No results for your query</body></html>",
        "x" * 10 + "g-recaptcha",  # the name in plain text (a snippet about reCAPTCHA) is not the widget
    ],
)
def test_ordinary_pages_are_not_flagged(html):
    assert not looks_blocked(html)


def test_a_captcha_page_is_a_challenge_not_a_no_results_error():
    class FakeResponse:
        status_code, text, url = 200, CAPTCHA_PAGE, "https://www.mojeek.com/search"

    engine = MojeekEngine()
    engine.session.get = lambda *a, **k: FakeResponse()
    with pytest.raises(ChallengeError):
        engine.search("php2shell")
    FakeResponse.text = OK_PAGE
    with pytest.raises(EngineError) as err:
        engine.search("php2shell")
    assert not isinstance(err.value, ChallengeError) and "No results" in str(err.value)


def test_challenge_error_is_a_rate_limit_error_for_existing_handlers():
    assert issubclass(ChallengeError, RateLimitError)


# --- health memory -------------------------------------------------------------------------------------------------
def test_only_blocks_make_an_engine_rest_and_the_rest_doubles_up_to_a_cap():
    clock = FakeClock()
    health = EngineHealth(cooldown_s=60, max_cooldown_s=200, clock=clock)
    health.record_failure("a", EngineError("a", "parse problem"))
    assert not health.is_resting("a")
    health.record_failure("a", RateLimitError("a", "429"))
    assert health.is_resting("a") and health.status()["a"]["rest_left_s"] == 60
    clock.t += 61
    assert not health.is_resting("a")
    health.record_failure("a", ChallengeError("a", "captcha"))
    assert health.status()["a"]["rest_left_s"] == 120
    health.record_failure("a", ChallengeError("a", "captcha"))
    health.record_failure("a", ChallengeError("a", "captcha"))
    assert health.status()["a"]["rest_left_s"] == 200 and health.status()["a"]["consecutive_blocks"] == 4
    health.record_success("a")
    assert not health.is_resting("a") and health.status()["a"]["consecutive_blocks"] == 0


def test_a_blocked_engine_is_skipped_on_the_next_queries_and_comes_back_later():
    clock = FakeClock()
    health = EngineHealth(cooldown_s=300, clock=clock)
    blocked = ScriptedEngine("blocked", [ChallengeError("blocked", "captcha"), hit("blocked")])
    good = ScriptedEngine("good", [hit("good")])
    s = WebSearcher(engines=[blocked, good], cache=False, health=health)
    assert s.search("q1", use_cache=False).engine_used == "good" and blocked.calls == 1
    r = s.search("q2", use_cache=False)
    assert r.engine_used == "good" and blocked.calls == 1 and r.fallback_history == ["good"]  # not asked again
    clock.t += 301
    assert s.search("q3", use_cache=False).engine_used == "blocked" and blocked.calls == 2
    assert s.engine_status()["blocked"]["consecutive_blocks"] == 0  # success resets the memory


def test_zero_results_do_not_make_an_engine_rest():
    health = EngineHealth()
    quiet = ScriptedEngine("quiet", [[]])
    good = ScriptedEngine("good", [hit("good")])
    s = WebSearcher(engines=[quiet, good], cache=False, health=health)
    s.search("q1", use_cache=False)
    s.search("q2", use_cache=False)
    assert quiet.calls == 2 and not health.is_resting("quiet")


def test_when_every_engine_is_resting_they_are_all_tried_anyway():
    health = EngineHealth()
    a = ScriptedEngine("a", [RateLimitError("a", "429"), hit("a")])
    b = ScriptedEngine("b", [RateLimitError("b", "429")])
    s = WebSearcher(engines=[a, b], cache=False, health=health)
    with pytest.raises(AllEnginesFailedError):
        s.search("q1", use_cache=False)
    assert health.is_resting("a") and health.is_resting("b")
    assert s.search("q2", use_cache=False).engine_used == "a"  # last resort instead of failing without trying


def test_resting_engines_are_reported_in_the_error_of_a_failed_search():
    health = EngineHealth()
    a = ScriptedEngine("a", [RateLimitError("a", "429")])
    b = ScriptedEngine("b", [[]])
    s = WebSearcher(engines=[a, b], cache=False, health=health)
    with pytest.raises(AllEnginesFailedError):
        s.search("q1", use_cache=False)
    with pytest.raises(AllEnginesFailedError) as err:
        s.search("q2", use_cache=False)
    assert "resting" in str(err.value) and a.calls == 1


def test_fastest_strategy_also_skips_resting_engines():
    health = EngineHealth()
    a = ScriptedEngine("a", [ChallengeError("a", "captcha")])
    b = ScriptedEngine("b", [hit("b")])
    s = WebSearcher(engines=[a, b], cache=False, strategy=RotationStrategy.FASTEST, health=health)
    s.search("q1", use_cache=False)
    calls_after_first = a.calls
    s.search("q2", use_cache=False)
    assert a.calls == calls_after_first


def test_health_is_shared_between_throwaway_searchers_by_default():
    a1 = ScriptedEngine("shared-a", [RateLimitError("shared-a", "429")])
    b1 = ScriptedEngine("shared-b", [hit("shared-b")])
    WebSearcher(engines=[a1, b1], cache=False).search("q", use_cache=False)
    a2 = ScriptedEngine("shared-a", [hit("shared-a")])
    b2 = ScriptedEngine("shared-b", [hit("shared-b")])
    r = WebSearcher(engines=[a2, b2], cache=False).search("q", use_cache=False)  # a brand new searcher
    assert r.engine_used == "shared-b" and a2.calls == 0
