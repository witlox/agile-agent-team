"""Remote git providers (GitHub, GitLab) for PR/MR workflows."""

import asyncio
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class PullRequestConfig:
    """Configuration for creating a pull request."""

    title: str
    body: str
    base_branch: str
    head_branch: str
    draft: bool = False


@dataclass
class PullRequestResult:
    """Result from pull request operation."""

    success: bool
    url: Optional[str] = None
    number: Optional[int] = None
    error: Optional[str] = None


class RemoteGitProvider(ABC):
    """Abstract base class for remote git providers."""

    def __init__(self, workspace: Path, config: Dict):
        """Initialize provider.

        Args:
            workspace: Path to git repository
            config: Provider configuration (auth, repo info, etc.)
        """
        self.workspace = workspace
        self.config = config

    @abstractmethod
    async def create_pull_request(
        self, pr_config: PullRequestConfig
    ) -> PullRequestResult:
        """Create a pull/merge request."""
        pass

    @abstractmethod
    async def approve_pull_request(self, pr_number: int, comment: str = "") -> bool:
        """Approve a pull/merge request."""
        pass

    @abstractmethod
    async def merge_pull_request(
        self, pr_number: int, merge_method: str = "squash"
    ) -> bool:
        """Merge a pull/merge request."""
        pass

    async def _run_command(
        self, command: str, timeout: int = 30
    ) -> tuple[bool, str, str]:
        """Run a shell command and return (success, stdout, stderr)."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            success = proc.returncode == 0
            return (
                success,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )

        except asyncio.TimeoutError:
            return (False, "", "Command timed out")
        except Exception as e:
            return (False, "", str(e))


class GitHubProvider(RemoteGitProvider):
    """GitHub provider using gh CLI with single service account."""

    def __init__(self, workspace: Path, config: Dict):
        """Initialize GitHub provider.

        Config expected:
            token_env: Environment variable name for GitHub token
            author_name: Agent name for git commit attribution
            author_email: Agent email for git commit attribution
        """
        super().__init__(workspace, config)

        # Set GitHub token from environment
        token_env = config.get("token_env", "GITHUB_TOKEN")
        token = os.environ.get(token_env)
        if token:
            os.environ["GH_TOKEN"] = token

    async def create_pull_request(
        self, pr_config: PullRequestConfig
    ) -> PullRequestResult:
        """Create GitHub pull request using gh CLI."""
        # Escape quotes in title and body
        title = pr_config.title.replace('"', '\\"')
        body = pr_config.body.replace('"', '\\"')

        # Build gh pr create command
        cmd_parts = [
            "gh pr create",
            f'--title "{title}"',
            f'--body "{body}"',
            f"--base {pr_config.base_branch}",
            f"--head {pr_config.head_branch}",
        ]

        if pr_config.draft:
            cmd_parts.append("--draft")

        command = " ".join(cmd_parts)

        success, stdout, stderr = await self._run_command(command)

        if not success:
            return PullRequestResult(success=False, error=stderr)

        # Parse PR URL and number from output
        # gh CLI outputs URL on last line
        url = stdout.strip().split("\n")[-1] if stdout.strip() else None

        # Extract PR number from URL (e.g., /pull/123)
        pr_number = None
        if url and "/pull/" in url:
            try:
                pr_number = int(url.split("/pull/")[-1].split("/")[0])
            except (IndexError, ValueError):
                pass

        return PullRequestResult(success=True, url=url, number=pr_number)

    async def approve_pull_request(self, pr_number: int, comment: str = "") -> bool:
        """Approve GitHub PR using gh CLI."""
        cmd = f"gh pr review {pr_number} --approve"
        if comment:
            escaped_comment = comment.replace('"', '\\"')
            cmd += f' --body "{escaped_comment}"'

        success, _, _ = await self._run_command(cmd)
        return success

    async def merge_pull_request(
        self, pr_number: int, merge_method: str = "squash"
    ) -> bool:
        """Merge GitHub PR using gh CLI."""
        # gh CLI merge methods: merge, squash, rebase
        cmd = f"gh pr merge {pr_number} --{merge_method} --delete-branch"

        success, _, _ = await self._run_command(cmd)
        return success


class GitLabProvider(RemoteGitProvider):
    """GitLab provider using glab CLI with per-agent accounts."""

    def __init__(self, workspace: Path, config: Dict):
        """Initialize GitLab provider.

        Config expected:
            token_env: Environment variable name for agent's GitLab token
            author_name: Agent name for git commit attribution
            author_email: Agent email for git commit attribution
        """
        super().__init__(workspace, config)

        # Set GitLab token from environment
        token_env = config.get("token_env")
        if token_env:
            token = os.environ.get(token_env)
            if token:
                os.environ["GITLAB_TOKEN"] = token

    async def create_pull_request(
        self, pr_config: PullRequestConfig
    ) -> PullRequestResult:
        """Create GitLab merge request using glab CLI."""
        # Escape quotes in title and body
        title = pr_config.title.replace('"', '\\"')
        body = pr_config.body.replace('"', '\\"')

        # Build glab mr create command
        cmd_parts = [
            "glab mr create",
            f'--title "{title}"',
            f'--description "{body}"',
            f"--target-branch {pr_config.base_branch}",
            f"--source-branch {pr_config.head_branch}",
        ]

        if pr_config.draft:
            cmd_parts.append("--draft")

        command = " ".join(cmd_parts)

        success, stdout, stderr = await self._run_command(command)

        if not success:
            return PullRequestResult(success=False, error=stderr)

        # Parse MR URL and number from output
        url = stdout.strip().split("\n")[-1] if stdout.strip() else None

        # Extract MR number (e.g., !123)
        mr_number = None
        if url and "!" in url:
            try:
                mr_number = int(url.split("!")[-1].split("/")[0])
            except (IndexError, ValueError):
                pass

        return PullRequestResult(success=True, url=url, number=mr_number)

    async def approve_pull_request(self, pr_number: int, comment: str = "") -> bool:
        """Approve GitLab MR using glab CLI."""
        cmd = f"glab mr approve {pr_number}"
        if comment:
            escaped_comment = comment.replace('"', '\\"')
            cmd += f' --comment "{escaped_comment}"'

        success, _, _ = await self._run_command(cmd)
        return success

    async def merge_pull_request(
        self, pr_number: int, merge_method: str = "squash"
    ) -> bool:
        """Merge GitLab MR using glab CLI."""
        # glab merge methods: merge, squash
        cmd = f"glab mr merge {pr_number}"
        if merge_method == "squash":
            cmd += " --squash"
        cmd += " --remove-source-branch"

        success, _, _ = await self._run_command(cmd)
        return success


def create_provider(
    provider_type: str, workspace: Path, config: Dict
) -> Optional[RemoteGitProvider]:
    """Factory function to create provider instance.

    Args:
        provider_type: "github" or "gitlab"
        workspace: Path to git repository
        config: Provider configuration

    Returns:
        Provider instance or None if provider_type is invalid
    """
    providers = {"github": GitHubProvider, "gitlab": GitLabProvider}

    provider_class = providers.get(provider_type.lower())
    if provider_class:
        return provider_class(workspace, config)

    return None
