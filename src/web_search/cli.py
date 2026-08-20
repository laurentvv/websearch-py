"""Backward-compatible CLI alias."""

from websearch_py.cli import build_parser, main

__all__ = ["main", "build_parser"]

if __name__ == "__main__":
    import sys
    sys.exit(main())
