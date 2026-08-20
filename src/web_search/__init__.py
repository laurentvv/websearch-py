"""Backward-compatible alias for websearch_py."""

import websearch_py
from websearch_py import *
from websearch_py import __version__

__all__ = list(websearch_py.__all__) + ["__version__"]
