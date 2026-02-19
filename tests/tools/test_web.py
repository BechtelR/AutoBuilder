"""Tests for web fetch and search tools."""

import pytest

from app.tools.web import web_fetch, web_search
from tests.tools.conftest import require_tavily_key


@pytest.mark.network
async def test_web_fetch_html() -> None:
    """Fetching an HTML page extracts readable text."""
    result = await web_fetch("https://httpbin.org/html")
    # httpbin /html returns a page containing "Herman Melville"
    assert "Herman Melville" in result


@pytest.mark.network
async def test_web_fetch_non_html() -> None:
    """Fetching a non-HTML resource returns content."""
    result = await web_fetch("https://httpbin.org/robots.txt")
    assert len(result) > 0
    assert "Error" not in result


async def test_web_search_missing_tavily_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Search with missing TAVILY_API_KEY returns a clear error."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("AUTOBUILDER_SEARCH_PROVIDER", raising=False)
    result = await web_search("test query", provider="tavily")
    assert "TAVILY_API_KEY not set" in result


async def test_web_search_missing_brave_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Search with missing BRAVE_API_KEY returns a clear error."""
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    result = await web_search("test query", provider="brave")
    assert "BRAVE_API_KEY not set" in result


async def test_web_search_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Search with an unknown provider returns a clear error."""
    monkeypatch.delenv("AUTOBUILDER_SEARCH_PROVIDER", raising=False)
    result = await web_search("test query", provider="duckduckgo")
    assert "unknown search provider" in result
    assert "duckduckgo" in result


@require_tavily_key
@pytest.mark.network
async def test_web_search_tavily() -> None:
    """Tavily search returns formatted results (requires API key)."""
    result = await web_search("python programming", num_results=3, provider="tavily")
    assert "Error" not in result
    # Should have numbered results
    assert "1." in result
