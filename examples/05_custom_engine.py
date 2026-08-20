"""Exemple 5 : Création et enregistrement d'un moteur de recherche personnalisé."""

from websearch_py import BaseSearchEngine, EngineRegistry, SearchResult, WebSearcher


class WikipediaSearchEngine(BaseSearchEngine):
    """Moteur personnalisé interrogeant l'API OpenSearch de Wikipedia."""

    name = "wikipedia"
    display_name = "Wikipedia OpenSearch"

    def search(self, query: str, max_results: int = 10, language: str = "fr", region=None) -> list[SearchResult]:
        url = f"https://{language}.wikipedia.org/w/api.php"
        params = {
            "action": "opensearch",
            "search": query,
            "limit": str(max_results),
            "namespace": "0",
            "format": "json",
        }
        resp = self.session.get(url, params=params, headers=self.get_headers(), timeout=self.timeout)
        data = resp.json()

        # Format Wikipedia OpenSearch: [query, [titles], [descriptions], [urls]]
        titles = data[1]
        snippets = data[2]
        links = data[3]

        results = []
        for i in range(len(titles)):
            results.append(
                SearchResult(
                    titre=titles[i],
                    url=links[i],
                    extrait=snippets[i] if i < len(snippets) else "",
                    engine=self.name,
                    rank=i + 1,
                )
            )
        return results


if __name__ == "__main__":
    print("=== Moteur Personnalisé (Wikipedia) ===")
    # 1. Enregistrement dans le registre global
    EngineRegistry.register("wikipedia", WikipediaSearchEngine)

    # 2. Utilisation dans WebSearcher avec repli sur DuckDuckGo
    searcher = WebSearcher(engines=["wikipedia", "duckduckgo"])
    response = searcher.search("Albert Einstein", max_results=3)

    print(f"Moteur utilisé : {response.engine_used}")
    for res in response.results:
        print(f"[{res.rank}] {res.titre}")
        print(f"    URL     : {res.url}")
        print(f"    Extrait : {res.extrait}")
        print()
