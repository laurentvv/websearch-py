# Engine answer fixtures

Pages used by `tests/test_challenges.py`. Every file is a trimmed copy: scripts, styles, tracking tokens and
unrelated chrome were removed, class / id names and visible sentences were kept as answered.

## Captured live on 2026-11-10

Client: the library's own engines (requests, rotated desktop User-Agent), one request per endpoint, nonsense query.

| File | Endpoint | Answer |
| --- | --- | --- |
| `ddg_html_anomaly.html` | `POST html.duckduckgo.com/html/` | HTTP 202, anomaly modal ("bots use DuckDuckGo too") |
| `ddg_lite_no_results.html` | `POST lite.duckduckgo.com/lite/` | HTTP 200, genuine "No results found for" page |
| `yahoo_no_results.html` | `GET search.yahoo.com/search` | HTTP 200, no `div.algo`, only the "People also ask" widget |
| `mojeek_captcha.html` | `GET www.mojeek.com/search` | HTTP 200, ALTCHA captcha page titled "Captcha" |
| `brave_captcha.html` | `GET search.brave.com/search` | HTTP 429, "decided to schedule a captcha for you" |
| `google_enablejs.html` | `GET www.google.com/search?gbv=1` | HTTP 200, JavaScript wall (`/httpservice/retry/enablejs`) |
| `qwant_spa_no_results.html` | `GET lite.qwant.com/` | redirected to the `www.qwant.com` single-page app, no result markup |

`ddg_html_no_results.html` is the genuine "No results found for" page of `html.duckduckgo.com/html/`, read the same day
from a desktop browser because the scripted client only got the anomaly page.

The Qwant API answer of that day (`HTTP 403`, body `{"status":"error","data":{"error_code":50}}`) is inlined in the
tests.

## Reconstructed, not captured

A genuine "no results" page could not be obtained on 2026-11-10 for these engines: Bing and Brave relaxed the query and
returned results, Mojeek and Google only answered with their challenge. The files follow the markup these engines are
known to use and must be replaced by a capture when one is available.

- `bing_no_results.html` (`li.b_no`)
- `brave_no_results.html`
- `mojeek_no_results.html`
- `google_no_results.html` (basic HTML layout, "did not match any documents")
