"""Brownfield convention analysis - detect existing code standards."""

import re
from pathlib import Path
from typing import Any, Dict


class ConventionAnalyzer:
    """Analyzes existing codebases to infer conventions."""

    def __init__(self, workspace: Path):
        self.workspace = workspace

    def analyze(self, language: str) -> Dict:
        """Analyze workspace conventions for given language.

        Returns:
            Dictionary of detected conventions with confidence scores.
        """
        if language == "python":
            return self.analyze_python()
        elif language == "go":
            return self.analyze_go()
        elif language == "rust":
            return self.analyze_rust()
        elif language == "typescript":
            return self.analyze_typescript()
        elif language == "cpp":
            return self.analyze_cpp()
        else:
            return {}

    def analyze_python(self) -> Dict:
        """Analyze Python code conventions."""
        conventions: Dict[str, Any] = {
            "line_length": None,
            "quote_style": None,
            "indent_size": None,
            "has_type_hints": False,
            "has_docstrings": False,
            "import_style": None,
            "existing_tools": [],
        }

        # Find Python files
        py_files = list(self.workspace.glob("**/*.py"))
        if not py_files:
            return conventions

        # Sample first 10 files for analysis
        sample_files = py_files[:10]

        # Analyze line lengths
        line_lengths = []
        for file in sample_files:
            try:
                for line in file.read_text().split("\n"):
                    if line.strip() and not line.strip().startswith("#"):
                        line_lengths.append(len(line))
            except (UnicodeDecodeError, PermissionError):
                continue

        if line_lengths:
            # Find most common max line length (rounded to nearest 10)
            max_lengths = sorted(line_lengths, reverse=True)[:100]
            avg_max = sum(max_lengths) / len(max_lengths)
            conventions["line_length"] = int(round(avg_max / 10) * 10)

        # Analyze quote style
        quotes = {"single": 0, "double": 0}
        for file in sample_files:
            try:
                content = file.read_text()
                quotes["single"] += len(re.findall(r"'[^']*'", content))
                quotes["double"] += len(re.findall(r'"[^"]*"', content))
            except (UnicodeDecodeError, PermissionError):
                continue

        if sum(quotes.values()) > 0:
            conventions["quote_style"] = (
                "single" if quotes["single"] > quotes["double"] else "double"
            )

        # Analyze indentation
        indents = []
        for file in sample_files:
            try:
                for line in file.read_text().split("\n"):
                    if line and not line[0].isspace():
                        continue
                    indent = len(line) - len(line.lstrip())
                    if indent > 0:
                        indents.append(indent)
            except (UnicodeDecodeError, PermissionError):
                continue

        if indents:
            # Find GCD of indentations (common indent size)
            from math import gcd
            from functools import reduce

            conventions["indent_size"] = reduce(gcd, indents)

        # Check for type hints
        for file in sample_files:
            try:
                content = file.read_text()
                if re.search(r"def \w+\([^)]*: \w+", content):
                    conventions["has_type_hints"] = True
                    break
            except (UnicodeDecodeError, PermissionError):
                continue

        # Check for docstrings
        for file in sample_files:
            try:
                content = file.read_text()
                if '"""' in content or "'''" in content:
                    conventions["has_docstrings"] = True
                    break
            except (UnicodeDecodeError, PermissionError):
                continue

        # Check for existing tools
        if (self.workspace / "pyproject.toml").exists():
            pyproject_content = (self.workspace / "pyproject.toml").read_text()
            if "[tool.black]" in pyproject_content:
                conventions["existing_tools"].append("black")
            if (
                "[tool.ruff]" in pyproject_content
                or "[tool.flake8]" in pyproject_content
            ):
                conventions["existing_tools"].append("ruff/flake8")
            if "[tool.mypy]" in pyproject_content:
                conventions["existing_tools"].append("mypy")
            if "[tool.pytest" in pyproject_content:
                conventions["existing_tools"].append("pytest")

        return conventions

    def analyze_go(self) -> Dict:
        """Analyze Go code conventions."""
        conventions: Dict[str, Any] = {
            "has_go_mod": False,
            "has_golangci_config": False,
            "test_pattern": "table-driven",  # Go standard
            "existing_tools": [],
        }

        # Check for go.mod
        if (self.workspace / "go.mod").exists():
            conventions["has_go_mod"] = True
            conventions["existing_tools"].append("go modules")

        # Check for golangci-lint config
        if (self.workspace / ".golangci.yml").exists() or (
            self.workspace / ".golangci.yaml"
        ).exists():
            conventions["has_golangci_config"] = True
            conventions["existing_tools"].append("golangci-lint")

        # Check for Makefile
        if (self.workspace / "Makefile").exists():
            conventions["existing_tools"].append("make")

        return conventions

    def analyze_rust(self) -> Dict:
        """Analyze Rust code conventions."""
        conventions: Dict[str, Any] = {
            "has_cargo": False,
            "has_rustfmt_config": False,
            "edition": "2021",
            "existing_tools": [],
        }

        # Check for Cargo.toml
        cargo_toml = self.workspace / "Cargo.toml"
        if cargo_toml.exists():
            conventions["has_cargo"] = True
            conventions["existing_tools"].append("cargo")

            # Extract edition
            try:
                content = cargo_toml.read_text()
                match = re.search(r'edition\s*=\s*"(\d+)"', content)
                if match:
                    conventions["edition"] = match.group(1)
            except (UnicodeDecodeError, PermissionError):
                pass

        # Check for rustfmt config
        if (self.workspace / "rustfmt.toml").exists() or (
            self.workspace / ".rustfmt.toml"
        ).exists():
            conventions["has_rustfmt_config"] = True
            conventions["existing_tools"].append("rustfmt")

        return conventions

    def analyze_typescript(self) -> Dict:
        """Analyze TypeScript code conventions."""
        conventions: Dict[str, Any] = {
            "has_tsconfig": False,
            "has_eslint": False,
            "has_prettier": False,
            "strict_mode": False,
            "quote_style": None,
            "semicolons": True,
            "existing_tools": [],
        }

        # Check for tsconfig.json
        tsconfig = self.workspace / "tsconfig.json"
        if tsconfig.exists():
            conventions["has_tsconfig"] = True
            conventions["existing_tools"].append("typescript")

            try:
                import json

                config = json.loads(tsconfig.read_text())
                if config.get("compilerOptions", {}).get("strict"):
                    conventions["strict_mode"] = True
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Check for ESLint
        eslint_files = [".eslintrc.json", ".eslintrc.js", ".eslintrc.yml"]
        for eslint_file in eslint_files:
            if (self.workspace / eslint_file).exists():
                conventions["has_eslint"] = True
                conventions["existing_tools"].append("eslint")
                break

        # Check for Prettier
        prettier_files = [".prettierrc", ".prettierrc.json", ".prettierrc.js"]
        for prettier_file in prettier_files:
            if (self.workspace / prettier_file).exists():
                conventions["has_prettier"] = True
                conventions["existing_tools"].append("prettier")

                # Try to read Prettier config
                try:
                    prettier_path = self.workspace / prettier_file
                    if (
                        prettier_path.suffix == ".json"
                        or prettier_file == ".prettierrc"
                    ):
                        import json

                        config = json.loads(prettier_path.read_text())
                        conventions["quote_style"] = (
                            "single" if config.get("singleQuote") else "double"
                        )
                        conventions["semicolons"] = config.get("semi", True)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
                break

        # Sample TypeScript files for conventions
        ts_files = list(self.workspace.glob("**/*.ts"))[:5]
        if ts_files and not conventions["quote_style"]:
            # Analyze quote style from code
            single = 0
            double = 0
            for file in ts_files:
                try:
                    content = file.read_text()
                    single += len(re.findall(r"'[^']*'", content))
                    double += len(re.findall(r'"[^"]*"', content))
                except (UnicodeDecodeError, PermissionError):
                    continue

            if single + double > 0:
                conventions["quote_style"] = "single" if single > double else "double"

        return conventions

    def analyze_cpp(self) -> Dict:
        """Analyze C++ code conventions."""
        conventions: Dict[str, Any] = {
            "has_cmake": False,
            "has_clang_format": False,
            "has_clang_tidy": False,
            "cpp_standard": "17",
            "existing_tools": [],
        }

        # Check for CMakeLists.txt
        cmake_file = self.workspace / "CMakeLists.txt"
        if cmake_file.exists():
            conventions["has_cmake"] = True
            conventions["existing_tools"].append("cmake")

            # Extract C++ standard
            try:
                content = cmake_file.read_text()
                match = re.search(r"CMAKE_CXX_STANDARD\s+(\d+)", content)
                if match:
                    conventions["cpp_standard"] = match.group(1)
            except (UnicodeDecodeError, PermissionError):
                pass

        # Check for clang-format
        if (self.workspace / ".clang-format").exists():
            conventions["has_clang_format"] = True
            conventions["existing_tools"].append("clang-format")

        # Check for clang-tidy
        if (self.workspace / ".clang-tidy").exists():
            conventions["has_clang_tidy"] = True
            conventions["existing_tools"].append("clang-tidy")

        return conventions

    def generate_augmented_config(self, language: str, detected: Dict) -> Dict:
        """Generate configuration that augments detected conventions with standard tools.

        Args:
            language: Programming language
            detected: Detected conventions from analyze()

        Returns:
            Augmented configuration merging detected + standards
        """
        if language == "python":
            return self._augment_python(detected)
        elif language == "go":
            return self._augment_go(detected)
        elif language == "rust":
            return self._augment_rust(detected)
        elif language == "typescript":
            return self._augment_typescript(detected)
        elif language == "cpp":
            return self._augment_cpp(detected)
        else:
            return {}

    def _augment_python(self, detected: Dict) -> Dict:
        """Augment Python conventions with standards."""
        config = {
            "language": "python",
            "formatter": "black",
            "linter": "ruff",
            "type_checker": "mypy",
            "test_framework": "pytest",
            "line_length": detected.get("line_length", 88),  # Black default
            "target_python": "3.9",
        }

        # Add missing tools
        missing_tools = []
        if "black" not in detected.get("existing_tools", []):
            missing_tools.append("black")
        if "ruff" not in detected.get(
            "existing_tools", []
        ) and "flake8" not in detected.get("existing_tools", []):
            missing_tools.append("ruff")
        if "mypy" not in detected.get("existing_tools", []) and not detected.get(
            "has_type_hints"
        ):
            missing_tools.append("mypy")
        if "pytest" not in detected.get("existing_tools", []):
            missing_tools.append("pytest")

        config["tools_to_add"] = missing_tools

        return config

    def _augment_go(self, detected: Dict) -> Dict[str, Any]:
        """Augment Go conventions with standards."""
        config: Dict[str, Any] = {
            "language": "go",
            "formatter": "gofmt + goimports",
            "linter": "golangci-lint",
            "test_framework": "go test",
        }

        missing_tools = []
        if not detected.get("has_golangci_config"):
            missing_tools.append("golangci-lint config")

        config["tools_to_add"] = missing_tools

        return config

    def _augment_rust(self, detected: Dict) -> Dict:
        """Augment Rust conventions with standards."""
        config = {
            "language": "rust",
            "formatter": "rustfmt",
            "linter": "clippy",
            "test_framework": "cargo test",
            "edition": detected.get("edition", "2021"),
        }

        missing_tools = []
        if not detected.get("has_rustfmt_config"):
            missing_tools.append("rustfmt.toml")

        config["tools_to_add"] = missing_tools

        return config

    def _augment_typescript(self, detected: Dict) -> Dict:
        """Augment TypeScript conventions with standards."""
        config = {
            "language": "typescript",
            "formatter": "prettier",
            "linter": "eslint",
            "type_checker": "tsc",
            "test_framework": "jest",
            "quote_style": detected.get("quote_style", "single"),
            "semicolons": detected.get("semicolons", True),
        }

        missing_tools = []
        if not detected.get("has_tsconfig"):
            missing_tools.append("tsconfig.json")
        if not detected.get("has_eslint"):
            missing_tools.append("eslint config")
        if not detected.get("has_prettier"):
            missing_tools.append("prettier config")

        config["tools_to_add"] = missing_tools

        return config

    def _augment_cpp(self, detected: Dict) -> Dict:
        """Augment C++ conventions with standards."""
        config = {
            "language": "cpp",
            "formatter": "clang-format",
            "linter": "clang-tidy",
            "build_system": "cmake",
            "test_framework": "googletest",
            "cpp_standard": detected.get("cpp_standard", "17"),
        }

        missing_tools = []
        if not detected.get("has_cmake"):
            missing_tools.append("CMakeLists.txt")
        if not detected.get("has_clang_format"):
            missing_tools.append(".clang-format")
        if not detected.get("has_clang_tidy"):
            missing_tools.append(".clang-tidy")

        config["tools_to_add"] = missing_tools

        return config
