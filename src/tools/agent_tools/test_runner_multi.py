"""Multi-language test execution tools for agents."""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Any, List

from .base import Tool, ToolResult


class LanguageDetector:
    """Detects project language from workspace files."""

    @staticmethod
    def detect(workspace: Path) -> List[str]:
        """Detect languages present in workspace.

        Returns:
            List of detected languages (e.g., ['python', 'go', 'typescript'])
        """
        languages = []

        # Python: pyproject.toml, setup.py, requirements.txt, *.py files
        if (
            (workspace / "pyproject.toml").exists()
            or (workspace / "setup.py").exists()
            or (workspace / "requirements.txt").exists()
            or list(workspace.glob("**/*.py"))
        ):
            languages.append("python")

        # Go: go.mod, go.sum, *.go files
        if (workspace / "go.mod").exists() or list(workspace.glob("**/*.go")):
            languages.append("go")

        # Rust: Cargo.toml, Cargo.lock, *.rs files
        if (workspace / "Cargo.toml").exists() or list(workspace.glob("**/*.rs")):
            languages.append("rust")

        # TypeScript/JavaScript: package.json, tsconfig.json, *.ts files
        if (
            (workspace / "package.json").exists()
            or (workspace / "tsconfig.json").exists()
            or list(workspace.glob("**/*.ts"))
            or list(workspace.glob("**/*.tsx"))
        ):
            languages.append("typescript")

        # C++: CMakeLists.txt, *.cpp/*.h files
        if (workspace / "CMakeLists.txt").exists() or list(workspace.glob("**/*.cpp")):
            languages.append("cpp")

        return languages


class MultiLanguageTestRunner(Tool):
    """Detect language and run appropriate tests."""

    @property
    def name(self) -> str:
        return "run_tests"

    @property
    def description(self) -> str:
        return (
            "Auto-detect language and run tests (pytest/go test/cargo test/jest/gtest)"
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to tests (optional, auto-detects)",
                    "default": "",
                },
                "language": {
                    "type": "string",
                    "description": "Force specific language (python|go|rust|typescript|cpp)",
                    "default": "",
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Verbose test output",
                    "default": False,
                },
                "collect_coverage": {
                    "type": "boolean",
                    "description": "Collect code coverage metrics",
                    "default": True,
                },
            },
        }

    async def execute(
        self,
        path: str = "",
        language: str = "",
        verbose: bool = False,
        collect_coverage: bool = True,
    ) -> ToolResult:
        """Run tests with language auto-detection."""
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
                # Use first detected language
                language = detected[0]

            # Route to appropriate test runner
            if language == "python":
                return await self._run_python_tests(path, verbose, collect_coverage)
            elif language == "go":
                return await self._run_go_tests(path, verbose, collect_coverage)
            elif language == "rust":
                return await self._run_rust_tests(verbose, collect_coverage)
            elif language == "typescript":
                return await self._run_typescript_tests(path, verbose, collect_coverage)
            elif language == "cpp":
                return await self._run_cpp_tests(verbose)
            else:
                return ToolResult(
                    success=False, output="", error=f"Unsupported language: {language}"
                )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error running tests: {str(e)}"
            )

    async def _run_python_tests(
        self, path: str, verbose: bool, collect_coverage: bool
    ) -> ToolResult:
        """Run pytest tests."""
        cmd = ["pytest"]

        if path:
            cmd.append(path)
        else:
            cmd.append("tests/")

        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")

        if collect_coverage:
            cmd.extend(
                [
                    "--cov=src",
                    "--cov-report=term-missing",
                    "--cov-report=json",
                    "--cov-branch",
                ]
            )

        cmd.extend(["--tb=short", "--no-header"])

        return await self._run_command(cmd, "pytest")

    async def _run_go_tests(
        self, path: str, verbose: bool, collect_coverage: bool
    ) -> ToolResult:
        """Run go test."""
        cmd = ["go", "test"]

        if verbose:
            cmd.append("-v")

        if collect_coverage:
            cmd.extend(["-cover", "-coverprofile=coverage.out"])

        # Add race detector
        cmd.append("-race")

        # Test path
        if path:
            cmd.append(path)
        else:
            cmd.append("./...")

        result = await self._run_command(cmd, "go test")

        # Parse Go coverage if collected
        if result.success and collect_coverage:
            coverage = await self._parse_go_coverage()
            if coverage:
                result.metadata.update(coverage)

        return result

    async def _run_rust_tests(
        self, verbose: bool, collect_coverage: bool
    ) -> ToolResult:
        """Run cargo test."""
        cmd = ["cargo", "test"]

        if not verbose:
            cmd.append("--quiet")

        result = await self._run_command(cmd, "cargo test")

        # For Rust coverage, would need tarpaulin or similar
        # cargo install cargo-tarpaulin
        # cargo tarpaulin --out Json
        if result.success and collect_coverage:
            # Try to get coverage if tarpaulin is available
            coverage_cmd = ["cargo", "tarpaulin", "--out", "Json", "--quiet"]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *coverage_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.workspace),
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
                if proc.returncode == 0:
                    coverage_data = json.loads(stdout.decode())
                    if "coverage" in coverage_data:
                        result.metadata["line_coverage"] = round(
                            coverage_data["coverage"], 1
                        )
            except (FileNotFoundError, asyncio.TimeoutError, json.JSONDecodeError):
                # Tarpaulin not available or failed, skip coverage
                pass

        return result

    async def _run_typescript_tests(
        self, path: str, verbose: bool, collect_coverage: bool
    ) -> ToolResult:
        """Run Jest tests."""
        cmd = ["npm", "test", "--", "--passWithNoTests"]

        if verbose:
            cmd.append("--verbose")

        if collect_coverage:
            cmd.append("--coverage")

        if path:
            cmd.append(path)

        result = await self._run_command(cmd, "jest")

        # Parse Jest coverage from output
        if result.success and collect_coverage:
            coverage = self._parse_jest_coverage(result.output)
            if coverage:
                result.metadata.update(coverage)

        return result

    async def _run_cpp_tests(self, verbose: bool) -> ToolResult:
        """Run CTest (CMake tests)."""
        # First check if build directory exists
        build_dir = self.workspace / "build"
        if not build_dir.exists():
            return ToolResult(
                success=False,
                output="",
                error="Build directory not found. Run 'cmake -B build' first.",
            )

        cmd = ["ctest", "--test-dir", str(build_dir)]

        if verbose:
            cmd.append("--verbose")
        else:
            cmd.append("--output-on-failure")

        return await self._run_command(cmd, "ctest")

    async def _run_command(self, cmd: List[str], tool_name: str) -> ToolResult:
        """Execute command and return result."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.config.get("test_timeout", 300)
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"{tool_name} timed out (exceeded 5 minutes)",
                )

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                # Only append stderr if it contains actual errors (not just warnings)
                if proc.returncode != 0:
                    output += "\n" + stderr_text

            success = proc.returncode == 0

            # Parse test summary based on tool
            summary = self._parse_test_output(output, tool_name)

            return ToolResult(success=success, output=output.strip(), metadata=summary)

        except FileNotFoundError:
            return ToolResult(
                success=False,
                output="",
                error=f"{tool_name} not found - is it installed?",
            )

    def _parse_test_output(self, output: str, tool: str) -> Dict:
        """Parse test output for summary info."""
        summary = {"passed": 0, "failed": 0, "total": 0}

        if tool == "pytest":
            # "5 passed, 2 failed in 1.23s"
            match = re.search(r"(\d+)\s+passed", output)
            if match:
                summary["passed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+failed", output)
            if match:
                summary["failed"] = int(match.group(1))

        elif tool == "go test":
            # "ok  	package	0.123s	coverage: 85.5% of statements"
            # "FAIL	package	0.123s"
            if "PASS" in output or "ok" in output:
                summary["passed"] = 1
            elif "FAIL" in output:
                summary["failed"] = 1

        elif tool == "cargo test":
            # "test result: ok. 10 passed; 0 failed; 0 ignored"
            match = re.search(r"(\d+)\s+passed", output)
            if match:
                summary["passed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+failed", output)
            if match:
                summary["failed"] = int(match.group(1))

        elif tool == "jest":
            # "Tests:       5 passed, 5 total"
            match = re.search(r"Tests:.*?(\d+)\s+passed", output)
            if match:
                summary["passed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+failed", output)
            if match:
                summary["failed"] = int(match.group(1))

        elif tool == "ctest":
            # "100% tests passed, 0 tests failed out of 10"
            match = re.search(r"(\d+)\s+tests passed", output)
            if match:
                summary["passed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+tests failed", output)
            if match:
                summary["failed"] = int(match.group(1))

        summary["total"] = summary["passed"] + summary["failed"]
        return summary

    async def _parse_go_coverage(self) -> Dict:
        """Parse Go coverage output."""
        coverage_file = self.workspace / "coverage.out"
        if not coverage_file.exists():
            return {}

        try:
            # Run go tool cover to get percentage
            proc = await asyncio.create_subprocess_exec(
                "go",
                "tool",
                "cover",
                "-func=coverage.out",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)

            output = stdout.decode("utf-8")
            # Look for "total: (statements) XX.X%"
            match = re.search(r"total:.*?(\d+\.?\d*)%", output)
            if match:
                return {"line_coverage": float(match.group(1))}

        except (FileNotFoundError, asyncio.TimeoutError):
            pass

        return {}

    def _parse_jest_coverage(self, output: str) -> Dict:
        """Parse Jest coverage from output."""
        # Jest outputs coverage table, look for overall percentages
        # "All files      |   85.5 |   80.2 |   90.1 |   85.5 |"
        match = re.search(r"All files\s+\|\s+(\d+\.?\d*)", output)
        if match:
            return {"line_coverage": float(match.group(1))}
        return {}
