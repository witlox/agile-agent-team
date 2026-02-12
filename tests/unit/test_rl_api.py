"""Unit tests for Public RL API Package (F-15)."""


class TestRLImports:
    """Verify all public symbols are importable from src.rl."""

    def test_import_episode_runner(self):
        from src.rl import EpisodeResult, EpisodeRunner

        assert EpisodeRunner is not None
        assert EpisodeResult is not None

    def test_import_scenario_catalog(self):
        from src.rl import EPISODE_TYPES, ScenarioCatalog, ScenarioConfig

        assert ScenarioCatalog is not None
        assert ScenarioConfig is not None
        assert len(EPISODE_TYPES) == 13

    def test_import_observation(self):
        from src.rl import AgentObservation, Observation, ObservationExtractor

        assert ObservationExtractor is not None
        assert Observation is not None
        assert AgentObservation is not None

    def test_import_reward(self):
        from src.rl import RewardCalculator, RewardSignal, RewardWeights

        assert RewardCalculator is not None
        assert RewardSignal is not None
        assert RewardWeights is not None

    def test_import_behavioral_taxonomy(self):
        from src.rl import BEHAVIORAL_CODES, BehavioralCode, BehavioralScorer

        assert BehavioralScorer is not None
        assert BehavioralCode is not None
        assert len(BEHAVIORAL_CODES) == 30

    def test_import_action_space(self):
        from src.rl import (
            ACTION_SPACE_SPEC,
            ActionExecutor,
            AdjustSprintParams,
            InjectDisturbance,
            ModifyBacklog,
            ModifyTeamComposition,
            SwapAgentRole,
        )

        assert ActionExecutor is not None
        assert InjectDisturbance is not None
        assert SwapAgentRole is not None
        assert ModifyBacklog is not None
        assert ModifyTeamComposition is not None
        assert AdjustSprintParams is not None
        assert len(ACTION_SPACE_SPEC) == 5

    def test_import_checkpoint(self):
        from src.rl import Checkpoint, CheckpointManager

        assert CheckpointManager is not None
        assert Checkpoint is not None

    def test_import_config(self):
        from src.rl import ExperimentConfig, ExperimentConfigBuilder

        assert ExperimentConfigBuilder is not None
        assert ExperimentConfig is not None

    def test_import_phase_runner(self):
        from src.rl import PhaseResult, PhaseRunner

        assert PhaseRunner is not None
        assert PhaseResult is not None

    def test_import_runtime_registry(self):
        from src.rl import register_runtime

        assert callable(register_runtime)

    def test_all_exports_in_dunder_all(self):
        import src.rl as rl_module

        for name in rl_module.__all__:
            assert hasattr(rl_module, name), f"{name} in __all__ but not importable"
