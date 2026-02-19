"""Web fetch and search tools for ADK agents."""

import os
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.lib.logging import get_logger
from app.tools._shared import truncate_output

logger = get_logger("tools.web")

_ALLOWED_SCHEMES = frozenset({"http", "https"})


async def web_fetch(url: str) -> str:
    """Fetch and extract content from a URL. Supplements ADK's load_web_page if needed.

    Retrieves the given URL, extracts readable text from HTML pages,
    and returns raw text for non-HTML responses. Output is truncated
    to 10 000 characters.

    Args:
        url: The URL to fetch.

    Returns:
        The page text content, or an error description if the request failed.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return f"Error: URL scheme '{parsed.scheme}' not allowed (only http/https)"

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            text = response.text

            if "text/html" in content_type:
                soup = BeautifulSoup(text, "html.parser")
                text = soup.get_text(separator="\n", strip=True)

            return truncate_output(text, 10_000)
    except httpx.HTTPStatusError as exc:
        msg = f"Error: HTTP {exc.response.status_code} for {url}"
        logger.warning(msg)
        return msg
    except httpx.ConnectError as exc:
        msg = f"Error: connection failed for {url} ({exc})"
        logger.warning(msg)
        return msg
    except httpx.TimeoutException:
        msg = f"Error: request timed out for {url}"
        logger.warning(msg)
        return msg
    except Exception as exc:  # noqa: BLE001
        msg = f"Error fetching {url}: {exc}"
        logger.warning(msg)
        return msg


async def web_search(
    query: str,
    num_results: int = 5,
    provider: str | None = None,
) -> str:
    """Search the web via SearXNG, Brave, or Tavily API. No Gemini dependency.

    Dispatches to Tavily or Brave Search depending on the provider
    parameter or the AUTOBUILDER_SEARCH_PROVIDER environment variable.

    Args:
        query: The search query string.
        num_results: Maximum number of results to return (default 5).
        provider: Search provider name ("tavily" or "brave").
            Falls back to AUTOBUILDER_SEARCH_PROVIDER env var, then "tavily".

    Returns:
        A numbered list of search results (title, URL, snippet),
        or an error description if the search failed.
    """
    from app.config import get_settings

    resolved_provider = (provider or get_settings().search_provider).lower()

    try:
        if resolved_provider == "tavily":
            return await _search_tavily(query, num_results)
        elif resolved_provider == "brave":
            return await _search_brave(query, num_results)
        else:
            return f"Error: unknown search provider '{resolved_provider}'"
    except httpx.HTTPStatusError as exc:
        msg = f"Error: {resolved_provider} API returned HTTP {exc.response.status_code}"
        logger.warning(msg)
        return msg
    except httpx.ConnectError as exc:
        msg = f"Error: connection to {resolved_provider} failed ({exc})"
        logger.warning(msg)
        return msg
    except httpx.TimeoutException:
        msg = f"Error: {resolved_provider} request timed out"
        logger.warning(msg)
        return msg
    except Exception as exc:  # noqa: BLE001
        msg = f"Error during {resolved_provider} search: {exc}"
        logger.warning(msg)
        return msg


async def _search_tavily(query: str, num_results: int) -> str:
    """Execute a search via the Tavily API."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY not set"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json={
                "query": query,
                "max_results": num_results,
                "api_key": api_key,
            },
        )
        response.raise_for_status()
        data: dict[str, list[dict[str, str]]] = response.json()

    results = data.get("results", [])
    if not results:
        return "No results found."

    return _format_results(results)


async def _search_brave(query: str, num_results: int) -> str:
    """Execute a search via the Brave Search API."""
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        return "Error: BRAVE_API_KEY not set"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": num_results},
            headers={"X-Subscription-Token": api_key},
        )
        response.raise_for_status()
        data: dict[str, dict[str, list[dict[str, str]]]] = response.json()

    web_results = data.get("web", {}).get("results", [])
    if not web_results:
        return "No results found."

    return _format_results(web_results)


def _format_results(results: list[dict[str, str]]) -> str:
    """Format search results as a numbered list."""
    lines: list[str] = []
    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        snippet = result.get("snippet", result.get("description", ""))
        lines.append(f"{i}. {title}\n   {url}\n   {snippet}")
    return "\n\n".join(lines)
