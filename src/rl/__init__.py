"""Public RL integration API for dojo's AATEnv(gym.Env) wrapper.

Provides a clean import surface for the RL environment components::

    from src.rl import EpisodeRunner, ScenarioCatalog, RewardCalculator
    from src.rl import ActionExecutor, InjectDisturbance, SwapAgentRole
    from src.rl import CheckpointManager, BehavioralScorer
"""

# Episode harness
from ..orchestrator.episode_runner import EpisodeResult, EpisodeRunner

# Scenario catalog
from ..orchestrator.scenario_catalog import (
    EPISODE_TYPES,
    ScenarioCatalog,
    ScenarioConfig,
)

# Observation
from ..orchestrator.observation import (
    AgentObservation,
    Observation,
    ObservationExtractor,
)

# Reward
from ..orchestrator.reward import RewardCalculator, RewardSignal, RewardWeights

# Behavioral taxonomy
from ..orchestrator.behavioral_taxonomy import (
    BEHAVIORAL_CODES,
    BehavioralCode,
    BehavioralScorer,
)

# Action space
from ..orchestrator.action_space import (
    ACTION_SPACE_SPEC,
    ActionExecutor,
    AdjustSprintParams,
    InjectDisturbance,
    ModifyBacklog,
    ModifyTeamComposition,
    SwapAgentRole,
)

# Checkpointing
from ..orchestrator.checkpoint import Checkpoint, CheckpointManager

# Config builder
from ..orchestrator.config_builder import ExperimentConfigBuilder
from ..orchestrator.config import ExperimentConfig

# Phase runner
from ..orchestrator.phase_runner import PhaseResult, PhaseRunner

# Runtime registry
from ..agents.runtime.factory import register_runtime

__all__ = [
    # Episode harness
    "EpisodeRunner",
    "EpisodeResult",
    # Scenario catalog
    "ScenarioCatalog",
    "ScenarioConfig",
    "EPISODE_TYPES",
    # Observation
    "ObservationExtractor",
    "Observation",
    "AgentObservation",
    # Reward
    "RewardCalculator",
    "RewardSignal",
    "RewardWeights",
    # Behavioral taxonomy
    "BehavioralScorer",
    "BehavioralCode",
    "BEHAVIORAL_CODES",
    # Action space
    "ActionExecutor",
    "InjectDisturbance",
    "SwapAgentRole",
    "ModifyBacklog",
    "ModifyTeamComposition",
    "AdjustSprintParams",
    "ACTION_SPACE_SPEC",
    # Checkpointing
    "CheckpointManager",
    "Checkpoint",
    # Config
    "ExperimentConfigBuilder",
    "ExperimentConfig",
    # Phase runner
    "PhaseRunner",
    "PhaseResult",
    # Runtime
    "register_runtime",
]
