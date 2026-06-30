import os
from tavily import TavilyClient

_tavily: TavilyClient | None = None


def get_tavily() -> TavilyClient:
    global _tavily
    if _tavily is None:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY environment variable is not set")
        _tavily = TavilyClient(api_key=api_key)
    return _tavily


def search(query: str, max_results: int = 5) -> tuple[str, str]:
    """Returns (formatted_snippets, comma_joined_urls)."""
    response = get_tavily().search(query=query, max_results=max_results, search_depth="basic")
    results = response.get("results", [])
    snippets = "\n\n".join(f"Title: {r['title']}\nContent: {r['content']}" for r in results)
    sources = ", ".join(r["url"] for r in results)
    return snippets, sources
