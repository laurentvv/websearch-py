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
from websearch_py.engines import DuckDuckGoEngine, DuckDuckGoLiteEngine
from websearch_py.engines.base import looks_blocked
from websearch_py.exceptions import ChallengeError, EngineError, RateLimitError

DDG_HTML = "https://html.duckduckgo.com/html/"
DDG_LITE = "https://lite.duckduckgo.com/lite/"

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
