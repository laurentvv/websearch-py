"""Pytest fixtures and sample HTML responses for testing search engines."""

import pytest

SAMPLE_DDG_HTML = """
<!DOCTYPE html>
<html>
<head><title>DuckDuckGo Search</title></head>
<body>
    <div class="result results_links results_links_deep web-result">
        <div class="links_main result__body">
            <h2 class="result__title">
                <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.python.org%2F&rut=123">Welcome to Python.org</a>
            </h2>
            <a class="result__snippet" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.python.org%2F&rut=123">
                The official home of the Python Programming Language. Download Python, tutorials, documentation and more.
            </a>
        </div>
    </div>
    <div class="result results_links results_links_deep web-result">
        <div class="links_main result__body">
            <h2 class="result__title">
                <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fdocs.python.org%2F3%2F&rut=456">Python 3 Documentation</a>
            </h2>
            <a class="result__snippet" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fdocs.python.org%2F3%2F&rut=456">
                Comprehensive documentation for Python 3.14 and standard library modules.
            </a>
        </div>
    </div>
</body>
</html>
"""

SAMPLE_DDG_LITE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <table>
        <tr>
            <td>
                <a class="result-link" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Ffastapi.tiangolo.com%2F">FastAPI Framework</a>
            </td>
        </tr>
        <tr>
            <td class="result-snippet">FastAPI is a modern, fast (high-performance), web framework for building APIs with Python.</td>
        </tr>
    </table>
</body>
</html>
"""

SAMPLE_BING_HTML = """
<!DOCTYPE html>
<html>
<body>
    <ol id="b_results">
        <li class="b_algo">
            <h2>
                <a href="https://www.bing.com/ck/a?!&&p=abc&u=a1aHR0cHM6Ly93d3cucHl0aG9uLm9yZy8&ntb=1">Welcome to Python.org</a>
            </h2>
            <div class="b_caption">
                <p>The mission of the Python Software Foundation is to promote, protect, and advance the Python language.</p>
            </div>
        </li>
        <li class="b_algo">
            <h2>
                <a href="https://docs.python.org/tutorial/">The Python Tutorial</a>
            </h2>
            <div class="b_caption">
                <p class="b_algoSlug">Python is an easy to learn, powerful programming language.</p>
            </div>
        </li>
    </ol>
</body>
</html>
"""

SAMPLE_GOOGLE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="Gx5Zad">
        <a href="/url?q=https://www.python.org/&sa=U&ved=2ahUKEwj">
            <div class="vvjwJb">Python Official Website</div>
        </a>
        <div class="BNeawe s3v9rd AP7Wnd">Python is a programming language that lets you work quickly and integrate systems more effectively.</div>
    </div>
    <div class="Gx5Zad">
        <a href="/url?q=https://pypi.org/&sa=U&ved=2ahUKEwj2">
            <div class="vvjwJb">PyPI - The Python Package Index</div>
        </a>
        <div class="BNeawe s3v9rd AP7Wnd">Find, install and publish Python packages with the Python Package Index.</div>
    </div>
</body>
</html>
"""

SAMPLE_YAHOO_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div id="web">
        <div class="algo">
            <h3 class="title">
                <a href="https://r.search.yahoo.com/_ylt=Awr/RU=https%3a%2f%2fwww.python.org%2f/RK=2/RS=xyz">Welcome to Python.org</a>
            </h3>
            <div class="compText">
                <p>Official site for Python source code, installer binaries, documentation, and news.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

SAMPLE_QWANT_API_JSON = {
    "status": "success",
    "data": {
        "result": {
            "items": {
                "mainline": [
                    {
                        "type": "web",
                        "items": [
                            {
                                "title": "Python Language",
                                "url": "https://www.python.org/",
                                "desc": "Official programming language website.",
                            }
                        ],
                    }
                ]
            }
        }
    },
}

SAMPLE_BRAVE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="snippet" data-type="web">
        <a class="heading" href="https://www.python.org/">Welcome to Python</a>
        <p class="snippet-description">Python documentation and downloads.</p>
    </div>
</body>
</html>
"""

SAMPLE_MOJEEK_HTML = """
<!DOCTYPE html>
<html>
<body>
    <ul class="results-standard">
        <li>
            <a class="title" href="https://www.python.org/">Welcome to Python.org</a>
            <p class="s">Python programming resources and community.</p>
        </li>
    </ul>
</body>
</html>
"""
