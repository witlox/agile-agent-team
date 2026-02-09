"""Multi-language code formatting tools."""

import asyncio
from pathlib import Path
from typing import Dict, Any, List

from .base import Tool, ToolResult
from .test_runner_multi import LanguageDetector


class MultiLanguageFormatter(Tool):
    """Auto-detect language and run appropriate formatter."""

    @property
    def name(self) -> str:
        return "format_code"

    @property
    def description(self) -> str:
        return "Auto-detect language and format code (black/gofmt/rustfmt/prettier/clang-format)"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to format (optional, defaults to entire workspace)",
                    "default": ""
                },
                "language": {
                    "type": "string",
                    "description": "Force specific language (python|go|rust|typescript|cpp)",
                    "default": ""
                },
                "check_only": {
                    "type": "boolean",
                    "description": "Check formatting without modifying files",
                    "default": False
                }
            }
        }

    async def execute(
        self,
        path: str = "",
        language: str = "",
        check_only: bool = False
    ) -> ToolResult:
        """Format code with language-specific formatter."""
        try:
            # Detect language if not specified
            if not language:
                detected = LanguageDetector.detect(self.workspace)
                if not detected:
                    return ToolResult(
                        success=False,
                        output="",
                        error="No recognized language found in workspace"
                    )
                language = detected[0]

            # Route to appropriate formatter
            if language == "python":
                return await self._format_python(path, check_only)
            elif language == "go":
                return await self._format_go(path, check_only)
            elif language == "rust":
                return await self._format_rust(check_only)
            elif language == "typescript":
                return await self._format_typescript(path, check_only)
            elif language == "cpp":
                return await self._format_cpp(path, check_only)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unsupported language: {language}"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error formatting code: {str(e)}"
            )

    async def _format_python(self, path: str, check_only: bool) -> ToolResult:
        """Format Python code with Black."""
        cmd = ["black"]

        if check_only:
            cmd.append("--check")

        if path:
            cmd.append(path)
        else:
            cmd.append(".")

        return await self._run_formatter(cmd, "black")

    async def _format_go(self, path: str, check_only: bool) -> ToolResult:
        """Format Go code with gofmt and goimports."""
        # gofmt doesn't have check-only mode, it shows diff
        if check_only:
            cmd = ["gofmt", "-d"]
        else:
            cmd = ["gofmt", "-w"]

        if path:
            cmd.append(path)
        else:
            cmd.append(".")

        result = await self._run_formatter(cmd, "gofmt")

        # If successful and not check_only, also run goimports
        if result.success and not check_only:
            imports_cmd = ["goimports", "-w"]
            if path:
                imports_cmd.append(path)
            else:
                imports_cmd.append(".")

            imports_result = await self._run_formatter(imports_cmd, "goimports")
            if not imports_result.success:
                return imports_result

        return result

    async def _format_rust(self, check_only: bool) -> ToolResult:
        """Format Rust code with rustfmt."""
        cmd = ["cargo", "fmt"]

        if check_only:
            cmd.append("--check")

        return await self._run_formatter(cmd, "rustfmt")

    async def _format_typescript(self, path: str, check_only: bool) -> ToolResult:
        """Format TypeScript code with Prettier."""
        cmd = ["npx", "prettier"]

        if check_only:
            cmd.append("--check")
        else:
            cmd.append("--write")

        if path:
            cmd.append(path)
        else:
            cmd.append(".")

        return await self._run_formatter(cmd, "prettier")

    async def _format_cpp(self, path: str, check_only: bool) -> ToolResult:
        """Format C++ code with clang-format."""
        # Find all C++ files
        if path:
            files = [path]
        else:
            files = [
                str(f) for f in self.workspace.glob("**/*.cpp")
            ] + [
                str(f) for f in self.workspace.glob("**/*.h")
            ] + [
                str(f) for f in self.workspace.glob("**/*.hpp")
            ]

        if not files:
            return ToolResult(
                success=True,
                output="No C++ files found to format"
            )

        if check_only:
            cmd = ["clang-format", "--dry-run", "--Werror"] + files
        else:
            cmd = ["clang-format", "-i"] + files

        return await self._run_formatter(cmd, "clang-format")

    async def _run_formatter(self, cmd: List[str], tool_name: str) -> ToolResult:
        """Execute formatter command."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace)
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=60  # Formatters should be fast
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"{tool_name} timed out"
                )

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                if proc.returncode != 0:
                    output += "\n" + stderr_text

            success = proc.returncode == 0

            if success and not output:
                output = f"Code formatted successfully with {tool_name}"

            return ToolResult(
                success=success,
                output=output.strip()
            )

        except FileNotFoundError:
            return ToolResult(
                success=False,
                output="",
                error=f"{tool_name} not found - is it installed?"
            )
