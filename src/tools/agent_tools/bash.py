"""Shell command execution tool."""

import asyncio
import os
from typing import Dict, Any

from .base import Tool, ToolResult


class BashTool(Tool):
    """Execute shell commands in the workspace."""

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "Execute a shell command in the workspace directory"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 60)",
                    "default": 60,
                },
            },
            "required": ["command"],
        }

    async def execute(self, command: str, timeout: int = 60) -> ToolResult:  # type: ignore[override]
        """Execute shell command."""
        # Security checks
        if not self._is_safe_command(command):
            return ToolResult(
                success=False,
                output="",
                error=f"Command not allowed for security reasons: {command}",
            )

        try:
            # Create subprocess
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
                env=self._get_safe_env(),
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout}s",
                )

            # Combine output
            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n" + stderr.decode("utf-8", errors="replace")

            success = proc.returncode == 0

            return ToolResult(
                success=success,
                output=output.strip(),
                error=None
                if success
                else f"Command failed with exit code {proc.returncode}",
                metadata={"exit_code": proc.returncode},
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error executing command: {str(e)}"
            )

    def _is_safe_command(self, command: str) -> bool:
        """Check if command is safe to execute."""
        # Get security config
        allowed_commands = self.config.get(
            "allowed_commands",
            [
                # Version control
                "git",
                "gh",
                "glab",
                # Python
                "python",
                "pip",
                "pytest",
                "mypy",
                "black",
                "ruff",
                "flake8",
                # Go
                "go",
                "gofmt",
                "goimports",
                "golangci-lint",
                # Rust
                "cargo",
                # TypeScript / JavaScript
                "npm",
                "node",
                "npx",
                "tsc",
                # C++
                "cmake",
                "ctest",
                "make",
                "clang-format",
                "clang-tidy",
                # General file/shell operations
                "ls",
                "cat",
                "grep",
                "find",
                "mkdir",
                "touch",
                "echo",
                "cp",
                "mv",
                "rm",
                "head",
                "tail",
                "wc",
                "diff",
                "sort",
                "uniq",
                "sed",
                "awk",
                "tree",
                "env",
                "which",
                "tar",
                "curl",
                "wget",
            ],
        )

        blocked_patterns = self.config.get(
            "blocked_patterns",
            [
                r"rm\s+-rf\s+/",
                r"dd\s+if=",
                r"mkfs",
                r":\(\)\{.*:\|:.*\};:",  # Fork bomb
                r"chmod.*777",
                r"sudo",
                r"curl.*\|.*bash",
                r"wget.*\|.*sh",
            ],
        )

        # Check if first word is in allowed list
        first_word = command.split()[0] if command.strip() else ""

        # Allow if it's in allowed commands or a relative path
        if first_word not in allowed_commands and not first_word.startswith("./"):
            return False

        # Check blocked patterns
        import re

        for pattern in blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False

        return True

    def _get_safe_env(self) -> Dict[str, str]:
        """Get safe environment variables for subprocess."""
        # Start with minimal env
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
        }

        # Add Python-related vars if present
        for key in ["VIRTUAL_ENV", "PYTHONPATH"]:
            if key in os.environ:
                safe_env[key] = os.environ[key]

        return safe_env
