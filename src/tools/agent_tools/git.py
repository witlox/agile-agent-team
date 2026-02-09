"""Git operation tools."""

import asyncio
from typing import Dict, Any

from .base import Tool, ToolResult


class GitStatusTool(Tool):
    """Get git status of the workspace."""

    @property
    def name(self) -> str:
        return "git_status"

    @property
    def description(self) -> str:
        return "Show the working tree status (modified, staged, untracked files)"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self) -> ToolResult:
        """Run git status."""
        return await self._run_git_command("git status --short")

    async def _run_git_command(self, command: str) -> ToolResult:
        """Helper to run a git command."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n" + stderr.decode("utf-8", errors="replace")

            success = proc.returncode == 0

            return ToolResult(
                success=success,
                output=output.strip() if output.strip() else "(no output)",
                error=None
                if success
                else f"Git command failed with exit code {proc.returncode}",
            )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output="", error="Git command timed out")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error: {str(e)}")


class GitDiffTool(Tool):
    """Show git diff of changes."""

    @property
    def name(self) -> str:
        return "git_diff"

    @property
    def description(self) -> str:
        return "Show diff of unstaged changes"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Optional path to show diff for (default: all files)",
                    "default": ".",
                },
                "staged": {
                    "type": "boolean",
                    "description": "Show staged changes instead of unstaged",
                    "default": False,
                },
            },
        }

    async def execute(self, path: str = ".", staged: bool = False) -> ToolResult:
        """Run git diff."""
        cmd = "git diff --cached" if staged else "git diff"
        if path != ".":
            cmd += f" {path}"

        return await self._run_git_command(cmd)

    async def _run_git_command(self, command: str) -> ToolResult:
        """Helper to run a git command."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n" + stderr.decode("utf-8", errors="replace")

            success = proc.returncode == 0

            return ToolResult(
                success=success,
                output=output.strip() if output.strip() else "(no changes)",
                error=None if success else "Git command failed",
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error: {str(e)}")


class GitAddTool(Tool):
    """Stage files for commit."""

    @property
    def name(self) -> str:
        return "git_add"

    @property
    def description(self) -> str:
        return "Stage files for commit"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to stage",
                }
            },
            "required": ["files"],
        }

    async def execute(self, files: list) -> ToolResult:
        """Stage files."""
        if not files:
            return ToolResult(success=False, output="", error="No files specified")

        files_str = " ".join(f'"{f}"' for f in files)
        return await self._run_git_command(f"git add {files_str}")

    async def _run_git_command(self, command: str) -> ToolResult:
        """Helper to run a git command."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n" + stderr.decode("utf-8", errors="replace")

            success = proc.returncode == 0

            return ToolResult(
                success=success,
                output=output.strip()
                if output.strip()
                else "Files staged successfully",
                error=None if success else "Git add failed",
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error: {str(e)}")


class GitCommitTool(Tool):
    """Commit staged changes."""

    @property
    def name(self) -> str:
        return "git_commit"

    @property
    def description(self) -> str:
        return "Commit staged changes with a message"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Commit message"}
            },
            "required": ["message"],
        }

    async def execute(self, message: str) -> ToolResult:
        """Create commit."""
        # Escape message for shell
        safe_message = message.replace('"', '\\"').replace("'", "\\'")
        return await self._run_git_command(f'git commit -m "{safe_message}"')

    async def _run_git_command(self, command: str) -> ToolResult:
        """Helper to run a git command."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n" + stderr.decode("utf-8", errors="replace")

            success = proc.returncode == 0

            return ToolResult(
                success=success,
                output=output.strip() if output.strip() else "Commit created",
                error=None if success else "Git commit failed",
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error: {str(e)}")


class GitRemoteTool(Tool):
    """Configure git remote URL."""

    @property
    def name(self) -> str:
        return "git_remote"

    @property
    def description(self) -> str:
        return "Configure git remote URL (add or set-url)"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Remote name (default: origin)",
                    "default": "origin",
                },
                "url": {"type": "string", "description": "Remote URL (https or git)"},
                "action": {
                    "type": "string",
                    "description": "Action: add or set-url",
                    "enum": ["add", "set-url"],
                    "default": "add",
                },
            },
            "required": ["url"],
        }

    async def execute(
        self, url: str, name: str = "origin", action: str = "add"
    ) -> ToolResult:
        """Configure remote."""
        cmd = f"git remote {action} {name} {url}"
        return await self._run_git_command(cmd)

    async def _run_git_command(self, command: str) -> ToolResult:
        """Helper to run a git command."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n" + stderr.decode("utf-8", errors="replace")

            success = proc.returncode == 0

            return ToolResult(
                success=success,
                output=output.strip() if output.strip() else "Remote configured",
                error=None if success else "Git remote command failed",
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error: {str(e)}")


class GitPushTool(Tool):
    """Push branch to remote repository."""

    @property
    def name(self) -> str:
        return "git_push"

    @property
    def description(self) -> str:
        return "Push current branch to remote repository"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "remote": {
                    "type": "string",
                    "description": "Remote name (default: origin)",
                    "default": "origin",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name (default: current branch)",
                },
                "set_upstream": {
                    "type": "boolean",
                    "description": "Set upstream tracking (-u flag)",
                    "default": True,
                },
            },
        }

    async def execute(
        self, remote: str = "origin", branch: str = None, set_upstream: bool = True
    ) -> ToolResult:
        """Push to remote."""
        # Get current branch if not specified
        if not branch:
            cmd = "git rev-parse --abbrev-ref HEAD"
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
            )
            stdout, _ = await proc.communicate()
            branch = stdout.decode("utf-8").strip()

        # Build push command
        push_cmd = f"git push {remote} {branch}"
        if set_upstream:
            push_cmd = f"git push -u {remote} {branch}"

        return await self._run_git_command(push_cmd)

    async def _run_git_command(self, command: str) -> ToolResult:
        """Helper to run a git command."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=60
            )  # 60s for push

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n" + stderr.decode("utf-8", errors="replace")

            success = proc.returncode == 0

            return ToolResult(
                success=success,
                output=output.strip() if output.strip() else "Pushed successfully",
                error=None if success else "Git push failed",
            )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output="", error="Git push timed out")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error: {str(e)}")
