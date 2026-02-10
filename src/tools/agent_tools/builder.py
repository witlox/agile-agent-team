"""Multi-language build tools."""

import asyncio
from typing import Dict, Any, List, Optional

from .base import Tool, ToolResult
from .test_runner_multi import LanguageDetector


class MultiLanguageBuilder(Tool):
    """Auto-detect language and run appropriate build."""

    @property
    def name(self) -> str:
        return "build_code"

    @property
    def description(self) -> str:
        return "Auto-detect language and build project (pip install/go build/cargo build/npm install/cmake)"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "description": "Force specific language (python|go|rust|typescript|cpp)",
                    "default": "",
                },
                "release": {
                    "type": "boolean",
                    "description": "Build in release/production mode",
                    "default": False,
                },
                "clean": {
                    "type": "boolean",
                    "description": "Clean before building",
                    "default": False,
                },
            },
        }

    async def execute(  # type: ignore[override]
        self, language: str = "", release: bool = False, clean: bool = False
    ) -> ToolResult:
        """Build project with language-specific build tool."""
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

            # Route to appropriate builder
            if language == "python":
                return await self._build_python()
            elif language == "go":
                return await self._build_go(release, clean)
            elif language == "rust":
                return await self._build_rust(release, clean)
            elif language == "typescript":
                return await self._build_typescript(release)
            elif language == "cpp":
                return await self._build_cpp(release, clean)
            else:
                return ToolResult(
                    success=False, output="", error=f"Unsupported language: {language}"
                )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error building project: {str(e)}"
            )

    async def _build_python(self) -> ToolResult:
        """Build Python project (install dependencies)."""
        # Check for requirements file
        if (self.workspace / "requirements.txt").exists():
            cmd = ["pip", "install", "-r", "requirements.txt"]
        elif (self.workspace / "pyproject.toml").exists():
            cmd = ["pip", "install", "-e", "."]
        elif (self.workspace / "setup.py").exists():
            cmd = ["pip", "install", "-e", "."]
        else:
            return ToolResult(
                success=False,
                output="",
                error="No requirements.txt, pyproject.toml, or setup.py found",
            )

        return await self._run_build(cmd, "pip install")

    async def _build_go(self, release: bool, clean: bool) -> ToolResult:
        """Build Go project."""
        if clean:
            clean_result = await self._run_build(["go", "clean"], "go clean")
            if not clean_result.success:
                return clean_result

        # First download dependencies
        mod_result = await self._run_build(["go", "mod", "download"], "go mod download")
        if not mod_result.success:
            return mod_result

        # Then build
        cmd = ["go", "build"]

        if release:
            # Add optimization flags for release
            cmd.extend(["-ldflags", "-s -w"])  # Strip debug info

        cmd.append("./...")

        return await self._run_build(cmd, "go build")

    async def _build_rust(self, release: bool, clean: bool) -> ToolResult:
        """Build Rust project with Cargo."""
        if clean:
            clean_result = await self._run_build(["cargo", "clean"], "cargo clean")
            if not clean_result.success:
                return clean_result

        cmd = ["cargo", "build"]

        if release:
            cmd.append("--release")

        return await self._run_build(cmd, "cargo build")

    async def _build_typescript(self, release: bool) -> ToolResult:
        """Build TypeScript project with npm."""
        # First install dependencies
        install_result = await self._run_build(["npm", "install"], "npm install")
        if not install_result.success:
            return install_result

        # Then build if build script exists
        package_json = self.workspace / "package.json"
        if package_json.exists():
            import json

            try:
                package_data = json.loads(package_json.read_text())
                if "scripts" in package_data and "build" in package_data["scripts"]:
                    cmd = ["npm", "run", "build"]
                    if release:
                        # Set NODE_ENV for production build
                        return await self._run_build(
                            cmd, "npm run build", env={"NODE_ENV": "production"}
                        )
                    return await self._run_build(cmd, "npm run build")
            except json.JSONDecodeError:
                pass

        # If no build script, just return install result
        return install_result

    async def _build_cpp(self, release: bool, clean: bool) -> ToolResult:
        """Build C++ project with CMake."""
        build_dir = self.workspace / "build"

        if clean and build_dir.exists():
            import shutil

            shutil.rmtree(build_dir)

        # Configure with CMake
        build_dir.mkdir(exist_ok=True)

        cmake_cmd = ["cmake", "-B", "build"]

        if release:
            cmake_cmd.extend(["-DCMAKE_BUILD_TYPE=Release"])
        else:
            cmake_cmd.extend(["-DCMAKE_BUILD_TYPE=Debug"])

        # Enable compile commands for clang-tidy
        cmake_cmd.append("-DCMAKE_EXPORT_COMPILE_COMMANDS=ON")

        configure_result = await self._run_build(cmake_cmd, "cmake configure")
        if not configure_result.success:
            return configure_result

        # Build
        build_cmd = ["cmake", "--build", "build"]

        if release:
            build_cmd.extend(["--config", "Release"])

        return await self._run_build(build_cmd, "cmake build")

    async def _run_build(
        self, cmd: List[str], tool_name: str, env: Optional[Dict[str, str]] = None
    ) -> ToolResult:
        """Execute build command."""
        try:
            import os

            # Merge environment if provided
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
                env=exec_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=300  # Builds can be slow (5 minutes)
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
                # Build tools often output to stderr
                output += "\n" + stderr_text

            success = proc.returncode == 0

            if success and not output.strip():
                output = f"Build completed successfully ({tool_name})"

            return ToolResult(success=success, output=output.strip())

        except FileNotFoundError:
            return ToolResult(
                success=False,
                output="",
                error=f"{tool_name.split()[0]} not found - is it installed?",
            )
