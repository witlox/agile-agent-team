"""Web search and fetch tools for domain research."""

import os
import re
from html.parser import HTMLParser
from typing import Any, Dict, List

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from .base import Tool, ToolResult


class _HTMLTextExtractor(HTMLParser):
    """Simple HTML to plain-text converter."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: List[str] = []
        self._skip = False
        self._skip_tags = {"script", "style", "noscript", "svg"}

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._skip_tags:
            self._skip = True
        if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # Collapse runs of whitespace/newlines
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


def _is_mock_mode() -> bool:
    """Check whether mock mode is active."""
    return os.environ.get("MOCK_LLM", "").lower() == "true"


_MOCK_SEARCH_RESULTS = [
    {
        "title": "Task Management Software Market Analysis 2026",
        "url": "https://example.com/market-analysis",
        "snippet": (
            "The task management software market is projected to reach $6.7B "
            "by 2027. Key players include Asana, Monday.com, and Trello. "
            "Emerging trends: AI-assisted prioritization, developer-focused "
            "tools, and deep CI/CD integration."
        ),
    },
    {
        "title": "Developer Productivity Tools Comparison",
        "url": "https://example.com/dev-tools",
        "snippet": (
            "Engineers prefer lightweight tools that integrate with their "
            "existing workflow (GitHub, GitLab, VS Code). Top pain points: "
            "context switching, over-complex UIs, and poor API support."
        ),
    },
    {
        "title": "Building a Successful SaaS Product for Small Teams",
        "url": "https://example.com/saas-guide",
        "snippet": (
            "Successful SaaS products for small teams focus on fast "
            "onboarding (<5 min), opinionated defaults, and friction-free "
            "collaboration. Key metric: time to first value."
        ),
    },
]

_MOCK_FETCH_CONTENT = (
    "# Example Page Content\n\n"
    "This is mock content returned for domain research in test/mock mode.\n\n"
    "## Key Points\n"
    "- The market for task management tools is growing rapidly\n"
    "- Developer-focused tools are an underserved niche\n"
    "- Integration with CI/CD and version control is a key differentiator\n"
    "- Small teams value simplicity over feature breadth\n"
)


class WebSearchTool(Tool):
    """Search the web using a configurable search engine.

    Supports Brave, Google Custom Search, and Kagi APIs.
    In mock mode (MOCK_LLM=true) returns canned results without calling any API.
    """

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web for information. Returns a list of results "
            "with titles, URLs, and text snippets. Useful for market "
            "research, competitor analysis, and domain knowledge."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:  # type: ignore[override]
        """Execute a web search."""
        query = kwargs.get("query", "")
        max_results = int(kwargs.get("max_results", 5))

        if not query:
            return ToolResult(success=False, output="", error="No query provided")

        # Mock mode: return canned results
        if _is_mock_mode():
            return ToolResult(
                success=True,
                output=self._format_results(_MOCK_SEARCH_RESULTS[:max_results]),
            )

        # Read search engine config
        web_cfg = self.config.get("web_search", {})
        engine = web_cfg.get("engine", "brave")
        api_key_env = web_cfg.get("api_key_env", "")
        api_key = os.environ.get(api_key_env, "") if api_key_env else ""

        if not api_key:
            return ToolResult(
                success=False,
                output="",
                error=f"No API key found in env var '{api_key_env}'",
            )

        if not HTTPX_AVAILABLE:
            return ToolResult(
                success=False,
                output="",
                error="httpx package not installed",
            )

        try:
            if engine == "brave":
                results = await self._search_brave(query, api_key, max_results)
            elif engine == "google":
                results = await self._search_google(query, api_key, max_results)
            elif engine == "kagi":
                results = await self._search_kagi(query, api_key, max_results)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown search engine: {engine}",
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

        return ToolResult(success=True, output=self._format_results(results))

    # ----- engine implementations -----

    async def _search_brave(
        self, query: str, api_key: str, max_results: int
    ) -> List[Dict[str, str]]:
        """Call Brave Web Search API."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max_results},
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results: List[Dict[str, str]] = []
        for item in data.get("web", {}).get("results", [])[:max_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", ""),
                }
            )
        return results

    async def _search_google(
        self, query: str, api_key: str, max_results: int
    ) -> List[Dict[str, str]]:
        """Call Google Custom Search JSON API."""
        cx = self.config.get("web_search", {}).get("google_cx", "")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": api_key, "cx": cx, "q": query, "num": max_results},
            )
            resp.raise_for_status()
            data = resp.json()

        results: List[Dict[str, str]] = []
        for item in data.get("items", [])[:max_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                }
            )
        return results

    async def _search_kagi(
        self, query: str, api_key: str, max_results: int
    ) -> List[Dict[str, str]]:
        """Call Kagi Search API."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://kagi.com/api/v0/search",
                params={"q": query, "limit": max_results},
                headers={"Authorization": f"Bot {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

        results: List[Dict[str, str]] = []
        for item in data.get("data", [])[:max_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                }
            )
        return results

    # ----- formatting -----

    def _format_results(self, results: List[Dict[str, str]]) -> str:
        """Format search results as readable text."""
        if not results:
            return "No results found."
        parts: List[str] = []
        for i, r in enumerate(results, 1):
            parts.append(
                f"{i}. **{r['title']}**\n" f"   URL: {r['url']}\n" f"   {r['snippet']}"
            )
        return "\n\n".join(parts)


class WebFetchTool(Tool):
    """Fetch and extract text content from a URL.

    Strips HTML to plain text and truncates to a configurable limit.
    In mock mode returns canned content.
    """

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return (
            "Fetch a web page and extract its text content. "
            "Useful for reading articles, documentation, or competitor "
            "pages discovered via web_search."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return (default 10000)",
                    "default": 10000,
                },
            },
            "required": ["url"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:  # type: ignore[override]
        """Fetch a URL and return plain text."""
        url: str = kwargs.get("url", "")
        max_chars = int(kwargs.get("max_chars", 10000))

        if not url:
            return ToolResult(success=False, output="", error="No URL provided")

        # Basic URL validation
        if not url.startswith(("http://", "https://")):
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid URL (must start with http:// or https://): {url}",
            )

        # Mock mode
        if _is_mock_mode():
            content = _MOCK_FETCH_CONTENT[:max_chars]
            return ToolResult(success=True, output=content)

        if not HTTPX_AVAILABLE:
            return ToolResult(
                success=False,
                output="",
                error="httpx package not installed",
            )

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

        # Convert HTML to text
        text = self._html_to_text(html)

        # Truncate
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[...truncated]"

        return ToolResult(success=True, output=text)

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Strip HTML tags and return plain text."""
        extractor = _HTMLTextExtractor()
        try:
            extractor.feed(html)
        except Exception:
            # Fallback: crude regex strip
            return re.sub(r"<[^>]+>", " ", html).strip()
        return extractor.get_text()
