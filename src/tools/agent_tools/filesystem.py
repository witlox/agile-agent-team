"""Filesystem tools for reading, writing, and editing files."""

import re
from typing import Dict, Any

from .base import Tool, ToolResult


class ReadFileTool(Tool):
    """Read the contents of a file."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the complete contents of a file"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to workspace root",
                }
            },
            "required": ["path"],
        }

    async def execute(self, path: str) -> ToolResult:
        """Read file contents."""
        try:
            full_path = self._resolve_path(path)

            if not full_path.exists():
                return ToolResult(
                    success=False, output="", error=f"File not found: {path}"
                )

            if not full_path.is_file():
                return ToolResult(success=False, output="", error=f"Not a file: {path}")

            content = full_path.read_text(encoding="utf-8")
            lines = len(content.splitlines())

            return ToolResult(
                success=True,
                output=content,
                metadata={"lines": lines, "bytes": len(content)},
            )

        except UnicodeDecodeError:
            return ToolResult(
                success=False, output="", error=f"File is not UTF-8 text: {path}"
            )
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error reading file: {str(e)}"
            )


class WriteFileTool(Tool):
    """Write content to a file (creates directories if needed)."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file, creating it if it doesn't exist (overwrites existing files)"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to workspace root",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        }

    async def execute(self, path: str, content: str) -> ToolResult:
        """Write content to file."""
        try:
            full_path = self._resolve_path(path)

            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            full_path.write_text(content, encoding="utf-8")

            lines = len(content.splitlines())

            return ToolResult(
                success=True,
                output=f"Successfully wrote {lines} lines ({len(content)} bytes) to {path}",
                files_changed=[path],
                metadata={"lines": lines, "bytes": len(content)},
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error writing file: {str(e)}"
            )


class EditFileTool(Tool):
    """Edit a file by replacing exact text match."""

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return "Edit a file by replacing an exact text match with new text"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to workspace root",
                },
                "old_text": {
                    "type": "string",
                    "description": "Exact text to find and replace (must match exactly)",
                },
                "new_text": {"type": "string", "description": "Text to replace with"},
            },
            "required": ["path", "old_text", "new_text"],
        }

    async def execute(self, path: str, old_text: str, new_text: str) -> ToolResult:
        """Edit file by text replacement."""
        try:
            full_path = self._resolve_path(path)

            if not full_path.exists():
                return ToolResult(
                    success=False, output="", error=f"File not found: {path}"
                )

            # Read current content
            content = full_path.read_text(encoding="utf-8")

            # Check if old_text exists
            if old_text not in content:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Text to replace not found in {path}",
                )

            # Check if replacement is unique
            occurrences = content.count(old_text)
            if occurrences > 1:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Text to replace appears {occurrences} times in {path}. Please provide more context to make it unique.",
                )

            # Perform replacement
            new_content = content.replace(old_text, new_text)
            full_path.write_text(new_content, encoding="utf-8")

            return ToolResult(
                success=True,
                output=f"Successfully edited {path}",
                files_changed=[path],
                metadata={"occurrences": 1},
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error editing file: {str(e)}"
            )


class ListFilesTool(Tool):
    """List files matching a pattern."""

    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "List files in workspace matching a glob pattern"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g., '**/*.py', 'src/**/*.ts')",
                    "default": "**/*",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 100,
                },
            },
        }

    async def execute(
        self, pattern: str = "**/*", max_results: int = 100
    ) -> ToolResult:
        """List files matching pattern."""
        try:
            matches = []
            for path in self.workspace.glob(pattern):
                if path.is_file():
                    rel_path = path.relative_to(self.workspace)
                    matches.append(str(rel_path))
                    if len(matches) >= max_results:
                        break

            matches.sort()

            output = "\n".join(matches) if matches else "No files found"

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "count": len(matches),
                    "truncated": len(matches) >= max_results,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error listing files: {str(e)}"
            )


class SearchCodeTool(Tool):
    """Search for text patterns in code files."""

    @property
    def name(self) -> str:
        return "search_code"

    @property
    def description(self) -> str:
        return "Search for a text pattern in files (case-sensitive, supports regex)"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Text or regex pattern to search for",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern for files to search (e.g., '**/*.py')",
                    "default": "**/*",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of matches to return",
                    "default": 50,
                },
            },
            "required": ["pattern"],
        }

    async def execute(
        self, pattern: str, file_pattern: str = "**/*", max_results: int = 50
    ) -> ToolResult:
        """Search for pattern in files."""
        try:
            regex = re.compile(pattern)
            matches = []

            for file_path in self.workspace.glob(file_pattern):
                if not file_path.is_file():
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8")
                    lines = content.splitlines()

                    for line_num, line in enumerate(lines, 1):
                        if regex.search(line):
                            rel_path = file_path.relative_to(self.workspace)
                            matches.append(f"{rel_path}:{line_num}: {line.strip()}")

                            if len(matches) >= max_results:
                                break

                except (UnicodeDecodeError, PermissionError):
                    continue  # Skip binary or inaccessible files

                if len(matches) >= max_results:
                    break

            if not matches:
                output = f"No matches found for pattern: {pattern}"
            else:
                output = "\n".join(matches)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "count": len(matches),
                    "truncated": len(matches) >= max_results,
                },
            )

        except re.error as e:
            return ToolResult(
                success=False, output="", error=f"Invalid regex pattern: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error searching: {str(e)}"
            )
