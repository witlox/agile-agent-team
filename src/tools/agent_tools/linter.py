"""Multi-language code linting tools."""

import asyncio
from typing import Dict, Any, List

from .base import Tool, ToolResult
from .test_runner_multi import LanguageDetector


class MultiLanguageLinter(Tool):
    """Auto-detect language and run appropriate linter."""

    @property
    def name(self) -> str:
        return "lint_code"

    @property
    def description(self) -> str:
        return "Auto-detect language and lint code (ruff/golangci-lint/clippy/eslint/clang-tidy)"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to lint (optional, defaults to entire workspace)",
                    "default": "",
                },
                "language": {
                    "type": "string",
                    "description": "Force specific language (python|go|rust|typescript|cpp)",
                    "default": "",
                },
                "fix": {
                    "type": "boolean",
                    "description": "Auto-fix issues where possible",
                    "default": False,
                },
            },
        }

    async def execute(
        self, path: str = "", language: str = "", fix: bool = False
    ) -> ToolResult:
        """Lint code with language-specific linter."""
        try:
            # Detect language if not specified
            if not language:
                detected = LanguageDetector.detect(self.workspace)
                if not detected:
                    return ToolResult(
                        success=False,
                        output="",
                        error="No recognized language found in workspace",
                    )
                language = detected[0]

            # Route to appropriate linter
            if language == "python":
                return await self._lint_python(path, fix)
            elif language == "go":
                return await self._lint_go(path)
            elif language == "rust":
                return await self._lint_rust(fix)
            elif language == "typescript":
                return await self._lint_typescript(path, fix)
            elif language == "cpp":
                return await self._lint_cpp(path)
            else:
                return ToolResult(
                    success=False, output="", error=f"Unsupported language: {language}"
                )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error linting code: {str(e)}"
            )

    async def _lint_python(self, path: str, fix: bool) -> ToolResult:
        """Lint Python code with Ruff."""
        cmd = ["ruff", "check"]

        if fix:
            cmd.append("--fix")

        if path:
            cmd.append(path)
        else:
            cmd.append(".")

        return await self._run_linter(cmd, "ruff")

    async def _lint_go(self, path: str) -> ToolResult:
        """Lint Go code with golangci-lint."""
        cmd = ["golangci-lint", "run"]

        if path:
            cmd.append(path)

        return await self._run_linter(cmd, "golangci-lint")

    async def _lint_rust(self, fix: bool) -> ToolResult:
        """Lint Rust code with clippy."""
        cmd = ["cargo", "clippy", "--", "-D", "warnings"]

        if fix:
            # Clippy doesn't have auto-fix, but we can suggest running rustfix
            return ToolResult(
                success=False,
                output="",
                error="Clippy doesn't support auto-fix. Run 'cargo fix' for fixable issues.",
            )

        return await self._run_linter(cmd, "clippy")

    async def _lint_typescript(self, path: str, fix: bool) -> ToolResult:
        """Lint TypeScript code with ESLint."""
        cmd = ["npx", "eslint"]

        if fix:
            cmd.append("--fix")

        cmd.extend(["--ext", ".ts,.tsx"])

        if path:
            cmd.append(path)
        else:
            cmd.append(".")

        return await self._run_linter(cmd, "eslint")

    async def _lint_cpp(self, path: str) -> ToolResult:
        """Lint C++ code with clang-tidy."""
        # Find all C++ files
        if path:
            files = [path]
        else:
            files = [str(f) for f in self.workspace.glob("**/*.cpp")]

        if not files:
            return ToolResult(success=True, output="No C++ files found to lint")

        # clang-tidy needs compilation database
        if not (self.workspace / "compile_commands.json").exists():
            return ToolResult(
                success=False,
                output="",
                error="compile_commands.json not found. Run 'cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON' first.",
            )

        cmd = ["clang-tidy"] + files + ["--"]

        return await self._run_linter(cmd, "clang-tidy")

    async def _run_linter(self, cmd: List[str], tool_name: str) -> ToolResult:
        """Execute linter command."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=120  # Linters can be slow
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult(
                    success=False, output="", error=f"{tool_name} timed out"
                )

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                # Some linters output to stderr even on success
                if stderr_text and proc.returncode != 0:
                    output += "\n" + stderr_text

            success = proc.returncode == 0

            if success and not output:
                output = f"No linting issues found ({tool_name})"

            # Parse linting stats
            metadata = self._parse_lint_output(output, tool_name)

            return ToolResult(success=success, output=output.strip(), metadata=metadata)

        except FileNotFoundError:
            return ToolResult(
                success=False,
                output="",
                error=f"{tool_name} not found - is it installed?",
            )

    def _parse_lint_output(self, output: str, tool: str) -> Dict:
        """Parse linter output for statistics."""
        import re

        stats = {"errors": 0, "warnings": 0, "files_checked": 0}

        if tool == "ruff":
            # Look for "Found X errors"
            match = re.search(r"Found (\d+) error", output)
            if match:
                stats["errors"] = int(match.group(1))

        elif tool == "golangci-lint":
            # Count issues by severity
            stats["errors"] = len(re.findall(r"^\S+:\d+:\d+:", output, re.MULTILINE))

        elif tool == "clippy":
            # Count warnings
            stats["warnings"] = len(re.findall(r"warning:", output))
            stats["errors"] = len(re.findall(r"error:", output))

        elif tool == "eslint":
            # Look for summary line
            match = re.search(
                r"(\d+) problems? \((\d+) errors?, (\d+) warnings?\)", output
            )
            if match:
                stats["errors"] = int(match.group(2))
                stats["warnings"] = int(match.group(3))

        elif tool == "clang-tidy":
            # Count warnings and errors
            stats["warnings"] = len(re.findall(r"warning:", output))
            stats["errors"] = len(re.findall(r"error:", output))

        return stats
