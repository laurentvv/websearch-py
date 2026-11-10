"""Bot challenges versus genuine "no results" answers, engine by engine (offline, see tests/fixtures/README.md)."""

from pathlib import Path

import pytest
import responses

from tests.conftest import (
    SAMPLE_BING_HTML,
    SAMPLE_BRAVE_HTML,
    SAMPLE_DDG_HTML,
    SAMPLE_DDG_LITE_HTML,
    SAMPLE_GOOGLE_HTML,
    SAMPLE_MOJEEK_HTML,
    SAMPLE_YAHOO_HTML,
)
from websearch_py import EngineHealth, WebSearcher
from websearch_py.engines import (
    BingEngine,
    BraveEngine,
    DuckDuckGoEngine,
    DuckDuckGoLiteEngine,
    EngineRegistry,
    GoogleEngine,
    MojeekEngine,
    QwantEngine,
    YahooEngine,
)
from websearch_py.engines.base import BaseSearchEngine, looks_blocked
from websearch_py.exceptions import ChallengeError, EngineError, RateLimitError
from websearch_py.models import SearchResult

DDG_HTML = "https://html.duckduckgo.com/html/"
DDG_LITE = "https://lite.duckduckgo.com/lite/"
QWANT_API = "https://api.qwant.com/v3/search/web"
QWANT_LITE = "https://lite.qwant.com/"
BING = "https://www.bing.com/search"
BRAVE = "https://search.brave.com/search"
GOOGLE = "https://www.google.com/search"
MOJEEK = "https://www.mojeek.com/search"
YAHOO = "https://search.yahoo.com/search"

QWANT_EMPTY_ANSWER = {"status": "success", "data": {"query": {"query": "x"}, "result": {"items": {"mainline": []}}}}
# How the bot protection in front of Qwant (DataDome) hands out its captcha: to API clients, then to browsers.
DATADOME_JSON = {"url": "https://geo.captcha-delivery.com/captcha/?initialCid=TOKEN&cid=TOKEN&t=fe&s=1"}
DATADOME_HTML = (
    "<html><head><title>qwant.com</title></head><body><p>Please enable JS and disable any ad blocker</p>"
    '<script src="https://ct.captcha-delivery.com/c.js"></script></body></html>'
)

FIXTURES = Path(__file__).parent / "fixtures"

CHALLENGE_PAGES = ["ddg_html_anomaly.html", "mojeek_captcha.html", "brave_captcha.html", "google_enablejs.html"]
NO_RESULT_PAGES = [
    "ddg_html_no_results.html",
    "ddg_lite_no_results.html",
    "yahoo_no_results.html",
    "qwant_spa_no_results.html",
    "bing_no_results.html",
    "brave_no_results.html",
    "mojeek_no_results.html",
    "google_no_results.html",
]

# Sentences a bot challenge would show, here quoted by an ordinary web page about captchas.
MARKER_WORDS = (
    "Why Google shows a captcha: our systems have detected unusual traffic, please verify you are human "
    "(g-recaptcha, h-captcha, cf-challenge, robot check)."
)


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def assert_plain_no_results(error: BaseException) -> None:
    """The error of a genuine empty answer: never a RateLimitError, so the engine is not put to rest."""
    assert isinstance(error, EngineError)
    assert not isinstance(error, RateLimitError)
    assert "No results found" in str(error)


# --- looks_blocked(): what a challenge page is -----------------------------------------------------------------------
@pytest.mark.parametrize("name", CHALLENGE_PAGES)
def test_captured_challenge_pages_are_recognised(name):
    assert looks_blocked(fixture(name))
    assert looks_blocked(fixture(name), query="python")


@pytest.mark.parametrize(
    "html",
    [
        '<html><body><form action="/verify"><div class="g-recaptcha" data-sitekey="k"></div></form></body></html>',
        '<html><body><iframe src="https://newassets.hcaptcha.com/captcha/v1/static/hcaptcha.html"></iframe></body></html>',
        '<html><body><script src="https://www.google.com/recaptcha/api.js" async></script></body></html>',
        (
            "<html><head><title>Just a moment...</title></head><body>"
            '<script src="/cdn-cgi/challenge-platform/h/b/orchestrate/chl_page/v1?ray=1"></script></body></html>'
        ),
        "<html><head><title>Attention Required! | Cloudflare</title></head><body><h1>Sorry</h1></body></html>",
        "<html><head><title>Captcha - Brave Search</title></head><body></body></html>",
        '<html><head><meta http-equiv="refresh" content="0;url=/sorry/index?continue=x"></head><body></body></html>',
        (
            "<html><body><div>Our systems have detected unusual traffic from your computer network. "
            '<a href="#">Why did this happen?</a></div></body></html>'
        ),
        "<html><body><h1>Are you a robot?</h1><p>Please complete the security check to continue.</p></body></html>",
    ],
)
def test_typical_challenge_pages_are_recognised(html):
    assert looks_blocked(html)


# --- looks_blocked(): what a challenge page is not -------------------------------------------------------------------
@pytest.mark.parametrize("name", NO_RESULT_PAGES)
def test_no_result_pages_are_not_challenges(name):
    assert not looks_blocked(fixture(name))


@pytest.mark.parametrize(
    ("page", "snippet"),
    [
        (SAMPLE_DDG_HTML, "The official home of the Python Programming Language."),
        (SAMPLE_DDG_LITE_HTML, "FastAPI is a modern, fast (high-performance), web framework"),
        (SAMPLE_BING_HTML, "The mission of the Python Software Foundation is to promote"),
        (SAMPLE_GOOGLE_HTML, "Python is a programming language that lets you work quickly"),
        (SAMPLE_YAHOO_HTML, "Official site for Python source code"),
        (SAMPLE_BRAVE_HTML, "Python documentation and downloads."),
        (SAMPLE_MOJEEK_HTML, "Python programming resources and community."),
    ],
)
def test_marker_words_in_a_result_snippet_are_not_a_block(page, snippet):
    assert snippet in page
    assert not looks_blocked(page.replace(snippet, MARKER_WORDS))


def test_marker_words_in_a_result_title_or_link_are_not_a_block():
    page = SAMPLE_BING_HTML.replace("Welcome to Python.org", "Captcha: unusual traffic, are you a robot?").replace(
        "https://docs.python.org/tutorial/", "https://example.org/g-recaptcha/captcha-challenge.html"
    )
    assert "g-recaptcha" in page
    assert not looks_blocked(page)


def test_a_page_title_that_starts_with_the_query_is_not_a_challenge_title():
    page = (
        "<html><head><title>captcha solver python - Search</title></head><body><ol id='b_results'></ol></body></html>"
    )
    assert not looks_blocked(page)
    assert not looks_blocked(page, query="captcha solver python")
    # Only the query tells "captcha - Search" (results for the word) from "Captcha - Brave Search" (a challenge).
    page = "<html><head><title>captcha - Search</title></head><body><ol id='b_results'></ol></body></html>"
    assert not looks_blocked(page, query="captcha")


def test_a_no_result_page_echoing_marker_words_is_not_a_block():
    query = "unusual traffic are you a robot"
    bing = fixture("bing_no_results.html").replace("qzxvjkwpytmnbvqzxplkwhgfd", query)
    assert not looks_blocked(bing)
    assert not looks_blocked(bing, query=query)
    bare = f"<html><head><title>{query} - Search</title></head><body><p>No results found for {query}</p></body></html>"
    assert not looks_blocked(bare, query=query)
    assert not looks_blocked(bare, query=f"  {query.upper()}  ")


def test_the_query_echoed_in_a_form_or_script_address_is_not_a_block():
    page = (
        '<html><body><form action="/search?q=captcha+challenge"><input name="q" value="captcha challenge"></form>'
        '<script src="/static/app.js?q=captcha"></script><p>No results</p></body></html>'
    )
    assert not looks_blocked(page)


@pytest.mark.parametrize("answer", ["", "   \n", '{"status":"error","data":{"error_code":50}}', "plain text"])
def test_empty_and_non_html_answers_are_not_challenges(answer):
    assert not looks_blocked(answer)


# --- DuckDuckGo ------------------------------------------------------------------------------------------------------
@responses.activate
def test_duckduckgo_http_202_is_a_challenge_and_stops_the_search():
    # The answer captured on 2026-11-10: HTTP 202 carrying the anomaly modal.
    responses.add(responses.POST, DDG_HTML, body=fixture("ddg_html_anomaly.html"), status=202)

    with pytest.raises(ChallengeError):
        DuckDuckGoEngine().search("python")
    assert len(responses.calls) == 1  # no GET retry, no Lite fallback: they would feed the bot detection


@responses.activate
def test_duckduckgo_http_202_on_the_get_retry_is_a_challenge():
    responses.add(responses.POST, DDG_HTML, body="<html><body></body></html>", status=200)
    responses.add(responses.GET, DDG_HTML, status=202)

    with pytest.raises(ChallengeError):
        DuckDuckGoEngine().search("python")
    assert len(responses.calls) == 2


@responses.activate
def test_duckduckgo_http_202_on_the_lite_fallback_is_a_challenge():
    responses.add(responses.POST, DDG_HTML, status=500)
    responses.add(responses.GET, DDG_HTML, status=500)
    responses.add(responses.POST, DDG_LITE, status=202)

    with pytest.raises(ChallengeError):
        DuckDuckGoEngine().search("python")


@responses.activate
def test_duckduckgo_anomaly_page_with_http_200_is_a_challenge():
    responses.add(responses.POST, DDG_HTML, body=fixture("ddg_html_anomaly.html"), status=200)

    with pytest.raises(ChallengeError):
        DuckDuckGoEngine().search("python")
    assert len(responses.calls) == 1


@responses.activate
@pytest.mark.parametrize("status", [403, 429])
def test_duckduckgo_refusals_stay_rate_limits(status):
    responses.add(responses.POST, DDG_HTML, status=status)

    with pytest.raises(RateLimitError) as err:
        DuckDuckGoEngine().search("python")
    assert not isinstance(err.value, ChallengeError)


@responses.activate
def test_duckduckgo_genuine_no_result_page_is_a_plain_error_after_one_request():
    responses.add(responses.POST, DDG_HTML, body=fixture("ddg_html_no_results.html"), status=200)

    with pytest.raises(EngineError) as err:
        DuckDuckGoEngine().search('"qzxvjkwpytmnbvqzxplkwhgfd" "xkqjzvwpqmznbxcvlkjh"')
    assert_plain_no_results(err.value)
    assert len(responses.calls) == 1  # the page is conclusive: no GET retry, no Lite fallback


@responses.activate
def test_duckduckgo_genuine_no_result_on_the_lite_fallback_is_a_plain_error():
    responses.add(responses.POST, DDG_HTML, status=500)
    responses.add(responses.GET, DDG_HTML, status=500)
    responses.add(responses.POST, DDG_LITE, body=fixture("ddg_lite_no_results.html"), status=200)

    with pytest.raises(EngineError) as err:
        DuckDuckGoEngine().search('"qzxvjkwpytmnbvqzxplkwhgfd" "xkqjzvwpqmznbxcvlkjh"')
    assert_plain_no_results(err.value)
    assert len(responses.calls) == 3


@responses.activate
def test_duckduckgo_unrecognised_empty_pages_are_a_plain_error_after_every_endpoint():
    for method, url in [(responses.POST, DDG_HTML), (responses.GET, DDG_HTML), (responses.POST, DDG_LITE)]:
        responses.add(method, url, body="<html><body><p>Something new</p></body></html>", status=200)
    responses.add(responses.GET, DDG_LITE, body="<html><body><p>Something new</p></body></html>", status=200)

    with pytest.raises(EngineError) as err:
        DuckDuckGoEngine().search("python")
    assert_plain_no_results(err.value)
    assert len(responses.calls) == 4


@responses.activate
def test_duckduckgo_lite_engine_http_202_is_a_challenge():
    responses.add(responses.POST, DDG_LITE, status=202)

    with pytest.raises(ChallengeError):
        DuckDuckGoLiteEngine().search("python")


@responses.activate
def test_duckduckgo_lite_engine_anomaly_page_with_http_200_is_a_challenge():
    responses.add(responses.POST, DDG_LITE, body=fixture("ddg_html_anomaly.html"), status=200)

    with pytest.raises(ChallengeError):
        DuckDuckGoLiteEngine().search("python")


@responses.activate
def test_duckduckgo_lite_engine_genuine_no_result_page_is_a_plain_error():
    responses.add(responses.POST, DDG_LITE, body=fixture("ddg_lite_no_results.html"), status=200)

    with pytest.raises(EngineError) as err:
        DuckDuckGoLiteEngine().search('"qzxvjkwpytmnbvqzxplkwhgfd" "xkqjzvwpqmznbxcvlkjh"')
    assert_plain_no_results(err.value)


# --- Qwant -----------------------------------------------------------------------------------------------------------
@responses.activate
@pytest.mark.parametrize("answer", [{"json": DATADOME_JSON}, {"body": DATADOME_HTML}])
def test_qwant_api_captcha_answer_is_a_challenge(answer):
    responses.add(responses.GET, QWANT_API, status=403, **answer)

    with pytest.raises(ChallengeError):
        QwantEngine().search("python")
    assert len(responses.calls) == 1  # the HTML fallback is not asked once the API said "captcha"


@responses.activate
def test_qwant_captcha_page_on_the_html_fallback_is_a_challenge():
    responses.add(responses.GET, QWANT_API, status=500)
    responses.add(responses.GET, QWANT_LITE, body=DATADOME_HTML, status=403)

    with pytest.raises(ChallengeError):
        QwantEngine().search("python")


@responses.activate
@pytest.mark.parametrize(
    ("status", "answer"),
    [
        (429, {"status": "error", "data": {"error_code": 24}}),
        (200, {"status": "error", "data": {"error_code": 24}}),
        (403, {"status": "error", "data": {"error_code": 50}}),  # the answer observed on 2026-11-10
    ],
)
def test_qwant_api_refusals_are_rate_limits(status, answer):
    responses.add(responses.GET, QWANT_API, json=answer, status=status)

    with pytest.raises(RateLimitError) as err:
        QwantEngine().search("python")
    assert not isinstance(err.value, ChallengeError)
    assert len(responses.calls) == 1


@responses.activate
def test_qwant_genuine_no_result_answer_is_a_plain_error():
    responses.add(responses.GET, QWANT_API, json=QWANT_EMPTY_ANSWER, status=200)
    responses.add(responses.GET, QWANT_LITE, body=fixture("qwant_spa_no_results.html"), status=200)

    with pytest.raises(EngineError) as err:
        QwantEngine().search("qzxvjkwpyt8842 mnbvqzxplk7731")
    assert_plain_no_results(err.value)


@responses.activate
def test_qwant_no_result_for_a_query_made_of_marker_words_is_a_plain_error():
    query = "captcha unusual traffic"
    page = fixture("qwant_spa_no_results.html").replace("qzxvjkwpyt8842 mnbvqzxplk7731", query)
    responses.add(responses.GET, QWANT_API, json=QWANT_EMPTY_ANSWER, status=200)
    responses.add(responses.GET, QWANT_LITE, body=page, status=200)

    with pytest.raises(EngineError) as err:
        QwantEngine().search(query)
    assert_plain_no_results(err.value)


# --- every engine: a genuine "no results" answer is a plain error and never a reason to rest ------------------------
def _json(payload):
    return {"json": payload}


def _page(name):
    return {"body": fixture(name)}


# engine class -> the mocked answers of a genuine empty search: (method, url, answer)
NO_RESULT_ANSWERS = {
    DuckDuckGoEngine: [(responses.POST, DDG_HTML, _page("ddg_html_no_results.html"))],
    DuckDuckGoLiteEngine: [(responses.POST, DDG_LITE, _page("ddg_lite_no_results.html"))],
    BingEngine: [(responses.GET, BING, _page("bing_no_results.html"))],
    GoogleEngine: [(responses.GET, GOOGLE, _page("google_no_results.html"))],
    YahooEngine: [(responses.GET, YAHOO, _page("yahoo_no_results.html"))],
    QwantEngine: [
        (responses.GET, QWANT_API, _json(QWANT_EMPTY_ANSWER)),
        (responses.GET, QWANT_LITE, _page("qwant_spa_no_results.html")),
    ],
    BraveEngine: [(responses.GET, BRAVE, _page("brave_no_results.html"))],
    MojeekEngine: [(responses.GET, MOJEEK, _page("mojeek_no_results.html"))],
}
ALL_ENGINES = pytest.mark.parametrize("engine_cls", list(NO_RESULT_ANSWERS), ids=lambda cls: cls.name)
# The nonsense queries the fixture pages were captured with.
FIXTURE_QUERIES = (
    '"qzxvjkwpytmnbvqzxplkwhgfd" "xkqjzvwpqmznbxcvlkjh"',
    "qzxvjkwpytmnbvqzxplkwhgfd xkqjzvwpqmznbxcvlkjh",
    "qzxvjkwpyt8842 mnbvqzxplk7731",
    "qzxvjkwpytmnbvqzxplkwhgfd",
)


def mock_no_result_answers(engine_cls, query: str | None = None) -> None:
    """Mock the genuine empty answer of an engine, optionally rewritten as the answer to another query."""
    for method, url, answer in NO_RESULT_ANSWERS[engine_cls]:
        if query and "body" in answer:
            body = answer["body"]
            for fixture_query in FIXTURE_QUERIES:
                body = body.replace(fixture_query, query)
            assert query in body
            answer = {"body": body}
        responses.add(method, url, status=200, **answer)


class AlwaysAnswers(BaseSearchEngine):
    name, display_name = "backup", "Backup"

    def search(self, query, max_results=10, language="en", region=None):
        return [SearchResult(titre="t", url="https://example.org", extrait="s", engine=self.name, rank=1)]


def test_every_registered_engine_has_a_no_result_fixture():
    assert sorted(cls.name for cls in NO_RESULT_ANSWERS) == EngineRegistry.list_available()


@responses.activate
@ALL_ENGINES
def test_a_genuine_no_result_answer_is_a_plain_error(engine_cls):
    mock_no_result_answers(engine_cls)

    with pytest.raises(EngineError) as err:
        engine_cls().search("qzxvjkwpytmnbvqzxplkwhgfd")
    assert_plain_no_results(err.value)


@responses.activate
@ALL_ENGINES
def test_a_no_result_answer_for_a_query_made_of_marker_words_is_a_plain_error(engine_cls):
    query = "captcha unusual traffic are you a robot"
    mock_no_result_answers(engine_cls, query)

    with pytest.raises(EngineError) as err:
        engine_cls().search(query)
    assert_plain_no_results(err.value)


@responses.activate
@ALL_ENGINES
def test_a_genuine_no_result_answer_does_not_put_the_engine_to_rest(engine_cls):
    mock_no_result_answers(engine_cls)
    health = EngineHealth()
    engine = engine_cls()
    searcher = WebSearcher(engines=[engine, AlwaysAnswers()], cache=False, health=health)

    for _ in range(2):
        response = searcher.search("qzxvjkwpytmnbvqzxplkwhgfd", use_cache=False)
        assert response.engine_used == "backup"
        assert response.fallback_history == [engine.name, "backup"]  # asked again: it was not resting
    assert not health.is_resting(engine.name)
    assert engine.name not in searcher.engine_status()


# --- every engine: a challenge answer puts it to rest ----------------------------------------------------------------
# engine class -> (method, url, status, answer); captured answers where one exists, a generic captcha page otherwise
CHALLENGE_ANSWERS = {
    DuckDuckGoEngine: (responses.POST, DDG_HTML, 202, _page("ddg_html_anomaly.html")),
    DuckDuckGoLiteEngine: (responses.POST, DDG_LITE, 202, _page("ddg_html_anomaly.html")),
    GoogleEngine: (responses.GET, GOOGLE, 200, _page("google_enablejs.html")),
    MojeekEngine: (responses.GET, MOJEEK, 200, _page("mojeek_captcha.html")),
    BraveEngine: (responses.GET, BRAVE, 200, _page("brave_captcha.html")),
    QwantEngine: (responses.GET, QWANT_API, 403, _json(DATADOME_JSON)),
    BingEngine: (responses.GET, BING, 200, {"body": DATADOME_HTML}),
    YahooEngine: (responses.GET, YAHOO, 200, {"body": DATADOME_HTML}),
}


@responses.activate
@ALL_ENGINES
def test_a_challenge_answer_is_a_challenge_error_and_puts_the_engine_to_rest(engine_cls):
    method, url, status, answer = CHALLENGE_ANSWERS[engine_cls]
    responses.add(method, url, status=status, **answer)
    health = EngineHealth()
    engine = engine_cls()
    searcher = WebSearcher(engines=[engine, AlwaysAnswers()], cache=False, health=health)

    with pytest.raises(ChallengeError):
        engine_cls().search("python")
    assert searcher.search("python", use_cache=False).engine_used == "backup"
    assert health.is_resting(engine.name)
    assert searcher.search("python again", use_cache=False).fallback_history == ["backup"]  # skipped while resting


@responses.activate
def test_brave_http_429_captcha_notice_is_a_rate_limit():
    # The answer captured on 2026-11-10: the status alone already says "blocked".
    responses.add(responses.GET, BRAVE, body=fixture("brave_captcha.html"), status=429)

    with pytest.raises(RateLimitError):
        BraveEngine().search("python")


def test_google_redirect_to_its_sorry_page_is_a_challenge():
    class SorryResponse:
        status_code, text = 200, "<html><body></body></html>"
        url = "https://www.google.com/sorry/index?continue=https://www.google.com/search%3Fq%3Dpython"

    engine = GoogleEngine()
    engine.session.get = lambda *args, **kwargs: SorryResponse()
    with pytest.raises(ChallengeError):
        engine.search("python")
