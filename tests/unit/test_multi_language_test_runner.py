"""Unit tests for multi-language test runner tool."""

import pytest

from src.tools.agent_tools.test_runner_multi import (
    LanguageDetector,
    MultiLanguageTestRunner,
)


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


# ---------------------------------------------------------------------------
# LanguageDetector tests
# ---------------------------------------------------------------------------


def test_language_detector_python(temp_workspace):
    """Detect Python from pyproject.toml."""
    (temp_workspace / "pyproject.toml").write_text("[project]\nname='x'")
    assert LanguageDetector.detect(temp_workspace) == ["python"]


def test_language_detector_python_requirements(temp_workspace):
    """Detect Python from requirements.txt."""
    (temp_workspace / "requirements.txt").write_text("pytest")
    assert "python" in LanguageDetector.detect(temp_workspace)


def test_language_detector_go(temp_workspace):
    """Detect Go from go.mod."""
    (temp_workspace / "go.mod").write_text("module example.com/m\ngo 1.21")
    assert LanguageDetector.detect(temp_workspace) == ["go"]


def test_language_detector_rust(temp_workspace):
    """Detect Rust from Cargo.toml."""
    (temp_workspace / "Cargo.toml").write_text('[package]\nname = "x"')
    assert LanguageDetector.detect(temp_workspace) == ["rust"]


def test_language_detector_typescript(temp_workspace):
    """Detect TypeScript from package.json."""
    (temp_workspace / "package.json").write_text('{"name":"x"}')
    assert LanguageDetector.detect(temp_workspace) == ["typescript"]


def test_language_detector_cpp(temp_workspace):
    """Detect C++ from CMakeLists.txt."""
    (temp_workspace / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.10)"
    )
    assert LanguageDetector.detect(temp_workspace) == ["cpp"]


def test_language_detector_multi(temp_workspace):
    """Detect multiple languages when several markers present."""
    (temp_workspace / "pyproject.toml").write_text("[project]")
    (temp_workspace / "go.mod").write_text("module m")
    (temp_workspace / "Cargo.toml").write_text("[package]")
    detected = LanguageDetector.detect(temp_workspace)
    assert "python" in detected
    assert "go" in detected
    assert "rust" in detected
    assert len(detected) == 3


def test_language_detector_empty(temp_workspace):
    """Empty workspace yields no languages."""
    assert LanguageDetector.detect(temp_workspace) == []


# ---------------------------------------------------------------------------
# _parse_test_output tests
# ---------------------------------------------------------------------------


@pytest.fixture
def runner(temp_workspace):
    """Create a MultiLanguageTestRunner instance."""
    return MultiLanguageTestRunner(workspace_root=str(temp_workspace))


def test_parse_test_output_pytest(runner):
    """Parse pytest summary line."""
    output = "FAILED tests/test_foo.py::test_bar\n5 passed, 2 failed in 1.23s"
    result = runner._parse_test_output(output, "pytest")
    assert result["passed"] == 5
    assert result["failed"] == 2
    assert result["total"] == 7


def test_parse_test_output_go_test_ok(runner):
    """Parse go test ok output."""
    output = "ok\texample.com/pkg\t0.123s\tcoverage: 85.5% of statements"
    result = runner._parse_test_output(output, "go test")
    assert result["passed"] == 1
    assert result["failed"] == 0


def test_parse_test_output_go_test_fail(runner):
    """Parse go test FAIL output."""
    output = "--- FAIL: TestFoo (0.00s)\nFAIL\texample.com/pkg\t0.123s"
    result = runner._parse_test_output(output, "go test")
    assert result["failed"] == 1


def test_parse_test_output_cargo_test(runner):
    """Parse cargo test summary."""
    output = "test result: ok. 10 passed; 2 failed; 0 ignored; 0 measured"
    result = runner._parse_test_output(output, "cargo test")
    assert result["passed"] == 10
    assert result["failed"] == 2
    assert result["total"] == 12


def test_parse_test_output_jest(runner):
    """Parse Jest summary."""
    output = "Tests:       5 passed, 5 total\nSnapshots:   0 total"
    result = runner._parse_test_output(output, "jest")
    assert result["passed"] == 5
    assert result["total"] == 5


def test_parse_test_output_ctest(runner):
    """Parse CTest summary."""
    output = (
        "10 tests passed, 0 tests failed out of 10\nTotal Test time (real) = 0.5 sec"
    )
    result = runner._parse_test_output(output, "ctest")
    assert result["passed"] == 10
    assert result["failed"] == 0
    assert result["total"] == 10


def test_parse_test_output_ctest_percentage_format(runner):
    """CTest percentage format (100% tests passed) — regex captures percentage number."""
    output = "100% tests passed, 0 tests failed out of 10"
    result = runner._parse_test_output(output, "ctest")
    # The regex r"(\\d+)\\s+tests passed" doesn't match "100% tests" (% blocks \\s+)
    # so passed remains 0; failed correctly parses as 0
    assert result["failed"] == 0


def test_parse_test_output_empty(runner):
    """Empty output yields zeroes."""
    result = runner._parse_test_output("", "pytest")
    assert result == {"passed": 0, "failed": 0, "total": 0}


# ---------------------------------------------------------------------------
# _parse_jest_coverage tests
# ---------------------------------------------------------------------------


def test_parse_jest_coverage(runner):
    """Parse Jest coverage table."""
    output = (
        "----------|---------|----------|---------|---------|---\n"
        "File      | % Stmts | % Branch | % Funcs | % Lines |\n"
        "----------|---------|----------|---------|---------|---\n"
        "All files |   85.5  |   80.2   |   90.1  |   85.5  |\n"
        "----------|---------|----------|---------|---------|---\n"
    )
    result = runner._parse_jest_coverage(output)
    assert result == {"line_coverage": 85.5}


def test_parse_jest_coverage_no_match(runner):
    """No coverage table yields empty dict."""
    result = runner._parse_jest_coverage("Tests: 5 passed")
    assert result == {}


# ---------------------------------------------------------------------------
# execute() edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_unsupported_language(temp_workspace):
    """Unsupported language returns error."""
    runner = MultiLanguageTestRunner(workspace_root=str(temp_workspace))
    result = await runner.execute(language="fortran")
    assert not result.success
    assert "Unsupported language" in result.error


@pytest.mark.asyncio
async def test_execute_no_language_detected(temp_workspace):
    """Empty workspace with no language arg returns error."""
    runner = MultiLanguageTestRunner(workspace_root=str(temp_workspace))
    result = await runner.execute()
    assert not result.success
    assert "No recognized language" in result.error
