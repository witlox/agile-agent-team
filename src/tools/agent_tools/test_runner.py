"""Test execution tools for agents."""

import asyncio
import json
from pathlib import Path
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
                },
                "collect_coverage": {
                    "type": "boolean",
                    "description": "Collect code coverage metrics using pytest-cov",
                    "default": True
                },
                "coverage_source": {
                    "type": "string",
                    "description": "Source directory to measure coverage for",
                    "default": "src"
                }
            }
        }

    async def execute(
        self,
        path: str = "tests/",
        verbose: bool = False,
        markers: str = "",
        collect_coverage: bool = True,
        coverage_source: str = "src"
    ) -> ToolResult:
        """Run pytest tests with optional coverage collection."""
        try:
            # Build pytest command
            cmd = ["pytest", path]

            if verbose:
                cmd.append("-v")
            else:
                cmd.append("-q")  # Quiet mode

            if markers:
                cmd.extend(["-m", markers])

            # Add coverage collection if enabled
            if collect_coverage:
                cmd.extend([
                    f"--cov={coverage_source}",  # Measure coverage of source
                    "--cov-report=json",  # Generate JSON report
                    "--cov-report=term-missing",  # Show missing lines in terminal
                    "--cov-branch"  # Include branch coverage
                ])

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

            # Parse coverage if collected
            if collect_coverage:
                coverage_data = self._parse_coverage_json()
                if coverage_data:
                    summary.update(coverage_data)

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

    def _parse_coverage_json(self) -> Dict:
        """Parse coverage.json for line and branch coverage metrics."""
        coverage_file = Path(self.workspace) / "coverage.json"

        if not coverage_file.exists():
            return {}

        try:
            coverage_data = json.loads(coverage_file.read_text())
            totals = coverage_data.get("totals", {})

            # Extract line coverage
            num_statements = totals.get("num_statements", 0)
            covered_lines = totals.get("covered_lines", 0)
            line_coverage = (covered_lines / num_statements * 100) if num_statements > 0 else 0.0

            # Extract branch coverage
            num_branches = totals.get("num_branches", 0)
            covered_branches = totals.get("covered_branches", 0)
            branch_coverage = (covered_branches / num_branches * 100) if num_branches > 0 else 0.0

            # Extract missing lines count
            missing_lines = totals.get("missing_lines", 0)

            return {
                "line_coverage": round(line_coverage, 1),
                "branch_coverage": round(branch_coverage, 1),
                "covered_lines": covered_lines,
                "total_lines": num_statements,
                "covered_branches": covered_branches,
                "total_branches": num_branches,
                "missing_lines": missing_lines
            }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If coverage parsing fails, return empty dict
            return {}


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
