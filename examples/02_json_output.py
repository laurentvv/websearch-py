import sys

from websearch_py import search_json

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("--- Sortie JSON Standard ---")
    query = "FastAPI documentation Python"

    # 1. Format JSON épuré : liste de [{titre, url, extrait}]
    clean_json = search_json(query, max_results=3, detailed=False, indent=2)
    print(clean_json)

    print("\n--- Sortie JSON Détaillée (avec métadonnées) ---")
    # 2. Format JSON détaillé : objet avec query, engine_used, cached, execution_time_ms, results
    detailed_json = search_json(query, max_results=2, detailed=True, indent=2)
    print(detailed_json)
