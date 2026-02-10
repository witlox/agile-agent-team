"""Tool factory for creating tool instances."""

from typing import List, Dict, Any, Optional

from .base import Tool
from .filesystem import (
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    ListFilesTool,
    SearchCodeTool,
)
from .bash import BashTool
from .git import (
    GitStatusTool,
    GitDiffTool,
    GitAddTool,
    GitCommitTool,
    GitRemoteTool,
    GitPushTool,
)
from .test_runner import RunBDDTestsTool
from .test_runner_multi import MultiLanguageTestRunner
from .formatter import MultiLanguageFormatter
from .linter import MultiLanguageLinter
from .builder import MultiLanguageBuilder
from .web import WebSearchTool, WebFetchTool


# Tool registry mapping names to classes
TOOL_REGISTRY = {
    "read_file": ReadFileTool,
    "write_file": WriteFileTool,
    "edit_file": EditFileTool,
    "list_files": ListFilesTool,
    "search_code": SearchCodeTool,
    "bash": BashTool,
    "git_status": GitStatusTool,
    "git_diff": GitDiffTool,
    "git_add": GitAddTool,
    "git_commit": GitCommitTool,
    "git_remote": GitRemoteTool,
    "git_push": GitPushTool,
    "run_tests": MultiLanguageTestRunner,
    "run_bdd_tests": RunBDDTestsTool,
    "format_code": MultiLanguageFormatter,
    "lint_code": MultiLanguageLinter,
    "build_code": MultiLanguageBuilder,
    "web_search": WebSearchTool,
    "web_fetch": WebFetchTool,
}

# Predefined tool sets
TOOL_SETS = {
    "filesystem": ["read_file", "write_file", "edit_file", "list_files", "search_code"],
    "git": [
        "git_status",
        "git_diff",
        "git_add",
        "git_commit",
        "git_remote",
        "git_push",
    ],
    "bash": ["bash"],
    "test_runner": ["run_tests", "run_bdd_tests"],
    "code_quality": ["format_code", "lint_code", "build_code"],
    "web": ["web_search", "web_fetch"],
    "basic": ["read_file", "write_file", "list_files"],
    "developer": [
        "read_file",
        "write_file",
        "edit_file",
        "list_files",
        "search_code",
        "git_status",
        "git_diff",
        "git_add",
        "git_commit",
        "format_code",
        "lint_code",
        "run_tests",
    ],
    "full": list(TOOL_REGISTRY.keys()),
}


def create_tools(
    tool_names: List[str], workspace_root: str, config: Optional[Dict[str, Any]] = None
) -> List[Tool]:
    """Create tool instances from a list of names.

    Args:
        tool_names: List of tool names or tool set names (e.g., ["filesystem", "git"])
        workspace_root: Root directory for file operations
        config: Optional tool-specific configuration

    Returns:
        List of instantiated Tool objects

    Raises:
        ValueError: If a tool name is not found in registry
    """
    config = config or {}
    tools = []
    seen = set()

    # Expand tool sets and collect unique tool names
    expanded_names = []
    for name in tool_names:
        if name in TOOL_SETS:
            # It's a tool set - expand it
            expanded_names.extend(TOOL_SETS[name])
        else:
            # It's a specific tool
            expanded_names.append(name)

    # Instantiate tools (avoiding duplicates)
    for name in expanded_names:
        if name in seen:
            continue

        tool_class = TOOL_REGISTRY.get(name)
        if tool_class is None:
            raise ValueError(
                f"Unknown tool: {name}. Available tools: {list(TOOL_REGISTRY.keys())}"
            )

        tool = tool_class(workspace_root=workspace_root, config=config)  # type: ignore[abstract]
        tools.append(tool)
        seen.add(name)

    return tools


def get_tool_names() -> List[str]:
    """Get list of all available tool names."""
    return list(TOOL_REGISTRY.keys())


def get_tool_set_names() -> List[str]:
    """Get list of predefined tool set names."""
    return list(TOOL_SETS.keys())
