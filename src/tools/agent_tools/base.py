"""Base classes for agent tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional


@dataclass
class ToolResult:
    """Result from tool execution."""

    success: bool
    output: str
    error: Optional[str] = None
    files_changed: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """Base class for all agent tools.

    Tools provide capabilities to agents (file operations, git, shell, etc.)
    They are runtime-agnostic and work with both Anthropic and vLLM runtimes.
    """

    def __init__(self, workspace_root: str, config: Optional[Dict] = None):
        """Initialize tool with workspace and configuration.

        Args:
            workspace_root: Root directory for file operations
            config: Optional tool-specific configuration
        """
        self.workspace = Path(workspace_root)
        self.config = config or {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for invocation (e.g., 'read_file')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON schema describing tool parameters.

        Example:
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            }
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters matching the schema

        Returns:
            ToolResult with execution outcome
        """
        pass

    def _resolve_path(self, path: str) -> "Path":
        """Resolve a path relative to workspace, with security checks.

        Args:
            path: Relative path from workspace root

        Returns:
            Absolute Path object

        Raises:
            ValueError: If path attempts to escape workspace
        """

        # Resolve relative to workspace
        full_path = (self.workspace / path).resolve()

        # Security: ensure path is within workspace
        try:
            full_path.relative_to(self.workspace)
        except ValueError:
            raise ValueError(f"Path {path} escapes workspace boundary")

        return full_path
