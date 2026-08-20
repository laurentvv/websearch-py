import sys
from web_search import search

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("--- Recherche simple avec WebSearch ---")
    query = "Python 3.14 nouvelles fonctionnalités"

    # Exécution de la recherche
    response = search(query, max_results=5, language="fr")

    print(f"Requête : {response.query}")
    print(f"Moteur utilisé : {response.engine_used}")
    print(f"En cache : {'OUI' if response.cached else 'NON'}")
    print(f"Temps d'exécution : {response.execution_time_ms:.1f}ms")
    print(f"Nombre de résultats : {len(response.results)}\n")

    for result in response.results:
        print(f"[{result.rank}] {result.titre}")
        print(f"    URL     : {result.url}")
        print(f"    Extrait : {result.extrait}")
        print()
