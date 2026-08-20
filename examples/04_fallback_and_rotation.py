"""Exemple 4 : Démonstration du Fallback automatique et de la Rotation des moteurs."""

from web_search import RotationStrategy, WebSearcher

if __name__ == "__main__":
    print("=== Démonstration Rotation Round-Robin ===")
    # Chaîne de moteurs avec Round-Robin : chaque nouvelle requête démarre sur un moteur différent
    searcher_rr = WebSearcher(
        engines=["duckduckgo", "bing", "yahoo", "qwant"],
        strategy=RotationStrategy.ROUND_ROBIN,
        cache=False,  # Désactiver le cache pour tester la rotation réseau
    )

    queries = [
        "Intelligence artificielle générative",
        "Algorithmes de tri en Python",
        "Frameworks web modernes",
    ]

    for i, q in enumerate(queries, 1):
        try:
            resp = searcher_rr.search(q, max_results=2)
            print(f"Requête {i} : '{q}'")
            print(f"  -> Moteur utilisé    : {resp.engine_used}")
            print(f"  -> Historique repli  : {resp.fallback_history}")
            print(f"  -> Temps d'exécution : {resp.execution_time_ms:.1f}ms")
            if resp.results:
                print(f"  -> Premier résultat  : {resp.results[0].titre} ({resp.results[0].url})")
            print()
        except Exception as e:
            print(f"Requête {i} échouée : {e}\n")
