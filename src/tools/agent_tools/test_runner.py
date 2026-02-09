"""Test execution tools for agents."""

import asyncio
from typing import Dict, Any

from .base import Tool, ToolResult


class RunTestsTool(Tool):
    """Run pytest tests and return results."""

    @property
    def name(self) -> str:
        return "run_tests"

    @property
    def description(self) -> str:
        return "Run pytest tests and return results (pass/fail counts, error messages)"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to tests (file or directory)",
                    "default": "tests/"
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Verbose output",
                    "default": False
                },
                "markers": {
                    "type": "string",
                    "description": "Pytest markers to filter (e.g., 'not slow')",
                    "default": ""
                }
            }
        }

    async def execute(
        self,
        path: str = "tests/",
        verbose: bool = False,
        markers: str = ""
    ) -> ToolResult:
        """Run pytest tests."""
        try:
            # Build pytest command
            cmd = ["pytest", path]

            if verbose:
                cmd.append("-v")
            else:
                cmd.append("-q")  # Quiet mode

            if markers:
                cmd.extend(["-m", markers])

            # Add options for clean output
            cmd.extend([
                "--tb=short",  # Short traceback format
                "--no-header",  # No pytest header
                "-p", "no:cacheprovider"  # Disable cache warnings
            ])

            # Run tests
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace)
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.config.get("test_timeout", 300)
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult(
                    success=False,
                    output="",
                    error="Tests timed out (exceeded 5 minutes)"
                )

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n" + stderr.decode("utf-8", errors="replace")

            success = proc.returncode == 0

            # Parse output for summary
            summary = self._parse_test_summary(output)

            return ToolResult(
                success=success,
                output=output.strip(),
                metadata=summary
            )

        except FileNotFoundError:
            return ToolResult(
                success=False,
                output="",
                error="pytest not found - is it installed?"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error running tests: {str(e)}"
            )

    def _parse_test_summary(self, output: str) -> Dict:
        """Parse pytest output for test counts."""
        import re

        summary = {
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "total": 0
        }

        # Look for pytest summary line like "5 passed, 2 failed in 1.23s"
        summary_pattern = r"(\d+)\s+(\w+)"
        matches = re.findall(summary_pattern, output)

        for count, status in matches:
            count = int(count)
            if "passed" in status:
                summary["passed"] = count
            elif "failed" in status:
                summary["failed"] = count
            elif "error" in status:
                summary["errors"] = count
            elif "skipped" in status:
                summary["skipped"] = count

        summary["total"] = summary["passed"] + summary["failed"] + summary["errors"]

        return summary


class RunBDDTestsTool(Tool):
    """Run BDD/Gherkin tests using pytest-bdd."""

    @property
    def name(self) -> str:
        return "run_bdd_tests"

    @property
    def description(self) -> str:
        return "Run BDD feature tests using pytest-bdd"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "feature_file": {
                    "type": "string",
                    "description": "Path to specific feature file (optional)",
                    "default": ""
                }
            }
        }

    async def execute(self, feature_file: str = "") -> ToolResult:
        """Run BDD tests."""
        try:
            # Build pytest command for BDD
            if feature_file:
                # Run specific feature
                cmd = ["pytest", "-v", "--tb=short", feature_file]
            else:
                # Run all features
                cmd = ["pytest", "-v", "--tb=short", "features/"]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace)
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n" + stderr.decode("utf-8", errors="replace")

            success = proc.returncode == 0

            return ToolResult(
                success=success,
                output=output.strip()
            )

        except FileNotFoundError:
            return ToolResult(
                success=False,
                output="",
                error="pytest or pytest-bdd not found"
            )
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error="BDD tests timed out"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error running BDD tests: {str(e)}"
            )
