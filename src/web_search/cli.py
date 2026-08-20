"""Command-line interface for web-search."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from web_search import (
    EngineRegistry,
    RotationStrategy,
    SQLiteCache,
    WebSearcher,
    __version__,
)


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="websearch",
        description="Fast & resilient web search scraper with fallback, engine rotation, and caching.",
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Search query text to look up.",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results to return (default: 10).",
    )
    parser.add_argument(
        "-l",
        "--language",
        type=str,
        default="fr",
        help="Search language code (e.g. 'fr', 'en', default: 'fr').",
    )
    parser.add_argument(
        "-r",
        "--region",
        type=str,
        default=None,
        help="Search region/country code (e.g. 'fr', 'us').",
    )
    parser.add_argument(
        "-e",
        "--engines",
        type=str,
        default=None,
        help="Comma-separated list of engines to use (e.g. 'duckduckgo,bing,google').",
    )
    parser.add_argument(
        "-s",
        "--strategy",
        type=str,
        choices=["fallback_priority", "round_robin", "random", "fastest"],
        default="fallback_priority",
        help="Rotation & fallback strategy (default: fallback_priority).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass and disable search cache.",
    )
    parser.add_argument(
        "--cache-backend",
        type=str,
        choices=["memory", "sqlite"],
        default="sqlite",
        help="Cache backend to use (default: sqlite).",
    )
    parser.add_argument(
        "--cache-db",
        type=str,
        default="search_cache.db",
        help="SQLite cache file path (default: search_cache.db).",
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=86400,
        help="Cache expiration Time-To-Live in seconds (default: 86400 / 24h).",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache database and exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results formatted as standard JSON array.",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Output full metadata in JSON (engine used, cache status, latency, fallback history).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Save output to specified JSON / text file.",
    )
    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="List all supported search engines and exit.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose / debug logging.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def main(args: Optional[list[str]] = None) -> int:
    """Main CLI entrypoint."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = build_parser()
    parsed_args = parser.parse_args(args)

    # Configure logging
    log_level = logging.DEBUG if parsed_args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 1. Handle --list-engines
    if parsed_args.list_engines:
        available = EngineRegistry.list_available()
        print("Available Search Engines:")
        for eng in available:
            print(f"  - {eng}")
        return 0

    # 2. Handle --clear-cache
    if parsed_args.clear_cache:
        with SQLiteCache(db_path=parsed_args.cache_db) as cache:
            cache.clear()
        print(f"Cache cleared successfully at '{parsed_args.cache_db}'.")
        return 0

    # Validate query
    if not parsed_args.query:
        parser.print_help()
        print("\nError: Please provide a search query.")
        return 1

    # Configure engines
    engine_list = None
    if parsed_args.engines:
        engine_list = [e.strip() for e in parsed_args.engines.split(",") if e.strip()]

    # Configure cache
    if parsed_args.no_cache:
        cache_config = False
    elif parsed_args.cache_backend == "sqlite":
        cache_config = parsed_args.cache_db
    else:
        cache_config = "memory"

    try:
        searcher = WebSearcher(
            engines=engine_list,
            cache=cache_config,
            strategy=parsed_args.strategy,
            cache_ttl=parsed_args.cache_ttl,
        )

        response = searcher.search(
            query=parsed_args.query,
            max_results=parsed_args.limit,
            language=parsed_args.language,
            region=parsed_args.region,
            use_cache=not parsed_args.no_cache,
        )

        # Format output
        if parsed_args.json or parsed_args.detailed or parsed_args.output:
            output_content = response.to_json(detailed=parsed_args.detailed, indent=2)
        else:
            # Human readable output
            lines = [
                f"\n=== Résultats pour '{response.query}' ===",
                f"Moteur: {response.engine_used} | Cache: {'OUI' if response.cached else 'NON'} | "
                f"Temps: {response.execution_time_ms:.1f}ms | Total: {len(response.results)}\n",
            ]
            for r in response.results:
                lines.append(f"[{r.rank}] {r.titre}")
                lines.append(f"    URL: {r.url}")
                if r.extrait:
                    lines.append(f"    Extrait: {r.extrait}")
                lines.append("")
            output_content = "\n".join(lines)

        # Output to file or stdout
        if parsed_args.output:
            Path(parsed_args.output).write_text(output_content, encoding="utf-8")
            print(f"Saved {len(response.results)} results to '{parsed_args.output}'.")
        else:
            print(output_content)

        return 0

    except Exception as e:
        sys.stderr.write(f"Search failed: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
