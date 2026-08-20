"""Exemple 3 : Gestion du cache pour requêtes identiques (Mémoire & SQLite)."""

import time
from web_search import SQLiteCache, WebSearcher

if __name__ == "__main__":
    print("=== 1. Test du Cache en Mémoire ===")
    searcher_mem = WebSearcher(cache="memory", cache_ttl=3600)

    query = "Bibliothèques Python machine learning"

    # Premier appel -> Cache MISS (requête réseau)
    t0 = time.perf_counter()
    resp1 = searcher_mem.search(query, max_results=3)
    t1 = time.perf_counter()
    print(f"Appel 1 (Réseau) : Cache={resp1.cached} | Moteur={resp1.engine_used} | Durée={(t1-t0)*1000:.1f}ms")

    # Deuxième appel avec requête identique (différence de casse/espaces) -> Cache HIT immédiat
    t2 = time.perf_counter()
    resp2 = searcher_mem.search("  BIBLIOTHÈQUES Python machine learning   ", max_results=3)
    t3 = time.perf_counter()
    print(f"Appel 2 (Cache)  : Cache={resp2.cached} | Moteur={resp2.engine_used} | Durée={(t3-t2)*1000:.1f}ms")
    print(f"Résultats identiques : {len(resp1.results) == len(resp2.results)}")

    print("\n=== 2. Test du Cache Persistant SQLite ===")
    with SQLiteCache(db_path="demo_cache.db", default_ttl_seconds=86400) as sqlite_cache:
        searcher_sqlite = WebSearcher(cache=sqlite_cache)

        resp_sql1 = searcher_sqlite.search("DuckDB SQL tutorial", max_results=2)
        print(f"SQLite Appel 1 : Cache={resp_sql1.cached} | Durée={resp_sql1.execution_time_ms:.1f}ms")

        resp_sql2 = searcher_sqlite.search("duckdb sql tutorial", max_results=2)
        print(f"SQLite Appel 2 : Cache={resp_sql2.cached} | Durée={resp_sql2.execution_time_ms:.1f}ms")
        print(f"Taille du cache SQLite : {sqlite_cache.size()} entrées")
