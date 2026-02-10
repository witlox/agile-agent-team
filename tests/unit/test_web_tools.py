"""Unit tests for WebSearchTool and WebFetchTool."""


import pytest

from src.tools.agent_tools.web import WebSearchTool, WebFetchTool


@pytest.fixture
def search_tool(tmp_path):
    """Create a WebSearchTool rooted at tmp_path."""
    return WebSearchTool(workspace_root=str(tmp_path), config={})


@pytest.fixture
def fetch_tool(tmp_path):
    """Create a WebFetchTool rooted at tmp_path."""
    return WebFetchTool(workspace_root=str(tmp_path), config={})


# ---------------------------------------------------------------------------
# WebSearchTool properties
# ---------------------------------------------------------------------------


def test_web_search_tool_properties(search_tool):
    """Tool exposes correct name, description, and parameter schema."""
    assert search_tool.name == "web_search"
    assert "search" in search_tool.description.lower()
    params = search_tool.parameters
    assert params["type"] == "object"
    assert "query" in params["properties"]
    assert "max_results" in params["properties"]
    assert "query" in params["required"]


# ---------------------------------------------------------------------------
# WebFetchTool properties
# ---------------------------------------------------------------------------


def test_web_fetch_tool_properties(fetch_tool):
    """Tool exposes correct name, description, and parameter schema."""
    assert fetch_tool.name == "web_fetch"
    assert "fetch" in fetch_tool.description.lower()
    params = fetch_tool.parameters
    assert params["type"] == "object"
    assert "url" in params["properties"]
    assert "max_chars" in params["properties"]
    assert "url" in params["required"]


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_mock_mode(search_tool, monkeypatch):
    """In mock mode, canned results are returned without calling any API."""
    monkeypatch.setenv("MOCK_LLM", "true")
    result = await search_tool.execute(query="task management tools")
    assert result.success is True
    assert len(result.output) > 0
    assert "Task Management" in result.output


@pytest.mark.asyncio
async def test_web_fetch_mock_mode(fetch_tool, monkeypatch):
    """In mock mode, canned content is returned without fetching."""
    monkeypatch.setenv("MOCK_LLM", "true")
    result = await fetch_tool.execute(url="https://example.com/page")
    assert result.success is True
    assert len(result.output) > 0
    assert "mock content" in result.output.lower()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_missing_api_key(tmp_path, monkeypatch):
    """Error returned when API key env var is not set."""
    monkeypatch.delenv("MOCK_LLM", raising=False)
    tool = WebSearchTool(
        workspace_root=str(tmp_path),
        config={"web_search": {"engine": "brave", "api_key_env": "MISSING_KEY_XYZ"}},
    )
    # Ensure the env var doesn't exist
    monkeypatch.delenv("MISSING_KEY_XYZ", raising=False)
    result = await tool.execute(query="test")
    assert result.success is False
    assert "MISSING_KEY_XYZ" in result.error


@pytest.mark.asyncio
async def test_web_search_unknown_engine(tmp_path, monkeypatch):
    """Error returned for an unsupported search engine."""
    monkeypatch.delenv("MOCK_LLM", raising=False)
    monkeypatch.setenv("TEST_KEY", "some-key")
    tool = WebSearchTool(
        workspace_root=str(tmp_path),
        config={"web_search": {"engine": "altavista", "api_key_env": "TEST_KEY"}},
    )
    result = await tool.execute(query="test")
    assert result.success is False
    assert "altavista" in result.error.lower()


@pytest.mark.asyncio
async def test_web_fetch_invalid_url(fetch_tool, monkeypatch):
    """Error returned for a URL missing the http(s) scheme."""
    monkeypatch.delenv("MOCK_LLM", raising=False)
    result = await fetch_tool.execute(url="not-a-url")
    assert result.success is False
    assert "Invalid URL" in result.error


@pytest.mark.asyncio
async def test_web_fetch_truncation(fetch_tool, monkeypatch):
    """Output is truncated to max_chars."""
    monkeypatch.setenv("MOCK_LLM", "true")
    result = await fetch_tool.execute(url="https://example.com", max_chars=50)
    assert result.success is True
    assert len(result.output) <= 50 + len("\n\n[...truncated]")
