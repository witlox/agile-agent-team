"""Fluent builder for ExperimentConfig — no YAML dependency.

Enables programmatic config construction for dojo's Gym wrapper
and other programmatic consumers.
"""

from typing import Any, Dict, List, Optional

from .config import ExperimentConfig


class ExperimentConfigBuilder:
    """Fluent builder for ExperimentConfig — no YAML dependency.

    Usage::

        config = (ExperimentConfigBuilder()
            .name("dojo-episode-42")
            .sprint_duration(5)
            .database_url("mock://")
            .tracing(True)
            .agents({
                "dev_lead": {"name": "Lead", "model": "mock", "runtime": "mock"},
            })
            .build()
        )
    """

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    # --- Core ---

    def name(self, name: str) -> "ExperimentConfigBuilder":
        """Set experiment name."""
        self._data.setdefault("experiment", {})["name"] = name
        return self

    def sprint_duration(self, minutes: int) -> "ExperimentConfigBuilder":
        """Set sprint duration in minutes."""
        self._data.setdefault("experiment", {})["sprint_duration_minutes"] = minutes
        return self

    def database_url(self, url: str) -> "ExperimentConfigBuilder":
        """Set database URL."""
        self._data.setdefault("database", {})["url"] = url
        return self

    def team_config_dir(self, path: str) -> "ExperimentConfigBuilder":
        """Set team_config directory path."""
        self._data.setdefault("team", {})["config_dir"] = path
        return self

    def vllm_endpoint(self, url: str) -> "ExperimentConfigBuilder":
        """Set vLLM endpoint URL."""
        self._data.setdefault("models", {})["vllm_endpoint"] = url
        return self

    # --- Agents ---

    def agents(self, configs: Dict[str, Dict[str, Any]]) -> "ExperimentConfigBuilder":
        """Set agent configurations.

        Args:
            configs: Mapping of agent_id to agent config dict.
        """
        self._data.setdefault("models", {})["agents"] = configs
        return self

    def runtimes(self, configs: Dict[str, Dict[str, Any]]) -> "ExperimentConfigBuilder":
        """Set runtime configurations."""
        self._data["runtimes"] = configs
        return self

    # --- Features ---

    def tracing(self, enabled: bool) -> "ExperimentConfigBuilder":
        """Enable or disable decision tracing (F-03/F-04)."""
        self._data.setdefault("experiment", {})["tracing"] = enabled
        return self

    def disturbances(
        self,
        enabled: bool = False,
        frequencies: Optional[Dict[str, float]] = None,
        blast_radius_controls: Optional[Dict[str, float]] = None,
    ) -> "ExperimentConfigBuilder":
        """Configure disturbance injection."""
        self._data["disturbances"] = {
            "enabled": enabled,
            "frequencies": frequencies or {},
            "blast_radius_controls": blast_radius_controls or {},
        }
        return self

    def attrition(self, **kwargs: Any) -> "ExperimentConfigBuilder":
        """Configure agent attrition (F-01).

        Keyword arguments are passed directly to the turnover config section.
        Common keys: enabled, starts_after_sprint, probability_per_sprint,
        backfill_enabled, backfill_delay_sprints, protect_roles,
        max_departures_per_sprint.
        """
        self._data.setdefault("team", {})["turnover"] = kwargs
        return self

    def onboarding(self, **kwargs: Any) -> "ExperimentConfigBuilder":
        """Configure new agent onboarding (F-02).

        Keyword arguments: duration_sprints, max_story_points_first_sprint,
        velocity_penalty_first_sprint.
        """
        self._data.setdefault("team", {})["onboarding"] = kwargs
        return self

    def profile_swapping(
        self,
        mode: str = "none",
        allowed_scenarios: Optional[List[str]] = None,
        penalties: Optional[Dict[str, float]] = None,
    ) -> "ExperimentConfigBuilder":
        """Configure profile swapping."""
        self._data["profile_swapping"] = {
            "mode": mode,
            "allowed_scenarios": allowed_scenarios or [],
            "penalties": penalties or {},
        }
        return self

    def workspace(
        self,
        root: str = "/tmp/agent-workspace",
        mode: str = "per_story",
    ) -> "ExperimentConfigBuilder":
        """Configure code generation workspace."""
        self._data.setdefault("runtimes", {}).setdefault("tools", {})[
            "workspace_root"
        ] = root
        self._data.setdefault("code_generation", {})["workspace_mode"] = mode
        return self

    def num_simulated_days(self, days: int) -> "ExperimentConfigBuilder":
        """Set number of simulated working days per sprint."""
        self._data.setdefault("experiment", {})["num_simulated_days"] = days
        return self

    def coordination(self, **kwargs: Any) -> "ExperimentConfigBuilder":
        """Configure cross-team coordination."""
        self._data["coordination"] = kwargs
        return self

    def messaging(self, **kwargs: Any) -> "ExperimentConfigBuilder":
        """Configure message bus (backend, redis_url, history_size, log_messages)."""
        self._data["messaging"] = kwargs
        return self

    # --- Build ---

    def build(self) -> ExperimentConfig:
        """Construct ExperimentConfig from accumulated settings.

        Missing values are filled in with defaults. No YAML file needed.
        """
        return ExperimentConfig.from_dict(self._data)
