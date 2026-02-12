"""Episode harness for RL environment integration.

Ties Phase B (config builder, phase runner, observation, reward, scenario
catalog) and Phase C (behavioral taxonomy, action space, checkpointing)
into a single-call episode execution API for dojo's ``AATEnv(gym.Env)``.
"""

import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .action_space import Action, ActionExecutor
from .behavioral_taxonomy import BehavioralScorer
from .checkpoint import CheckpointManager
from .config_builder import ExperimentConfigBuilder
from .observation import ObservationExtractor
from .phase_runner import PhaseResult, PhaseRunner
from .reward import RewardCalculator, RewardSignal, RewardWeights
from .scenario_catalog import ScenarioCatalog, ScenarioConfig

if TYPE_CHECKING:
    pass


@dataclass
class EpisodeResult:
    """Complete result of an episode execution."""

    episode_id: str
    episode_type: str
    stage: int
    difficulty: float
    phase_results: List[PhaseResult]
    final_observation: Dict[str, Any]
    reward: RewardSignal
    behavioral_score: float
    behaviors_detected: List[str]
    decision_traces: Dict[str, List[Dict[str, Any]]]
    sprint_result: Optional[Dict[str, Any]] = None
    total_duration_seconds: float = 0.0
    terminated: bool = True
    truncated: bool = False


class EpisodeRunner:
    """Single-call episode execution for dojo's AATEnv.

    Orchestrates scenario generation, sprint manager construction,
    phase execution, observation extraction, behavioral scoring,
    and reward computation.

    Usage::

        runner = EpisodeRunner()
        result = await runner.run_episode("implementation", difficulty=0.5)
    """

    def __init__(
        self,
        catalog: Optional[ScenarioCatalog] = None,
        reward_weights: Optional[RewardWeights] = None,
        checkpoint_dir: Optional[Path] = None,
        workspace_root: str = "/tmp/aat-episodes",
    ) -> None:
        self._catalog = catalog or ScenarioCatalog()
        self._reward = RewardCalculator(reward_weights)
        self._scorer = BehavioralScorer()
        self._checkpoint_mgr = CheckpointManager(checkpoint_dir)
        self._workspace_root = workspace_root

    async def run_episode(
        self,
        episode_type: str,
        difficulty: float = 0.5,
        target_slot: str = "dev_mid_backend",
        seed: Optional[int] = None,
        actions: Optional[List[Action]] = None,
        checkpoint_every_phase: bool = False,
    ) -> EpisodeResult:
        """Run a full episode by type.

        Args:
            episode_type: One of EPISODE_TYPES keys.
            difficulty: 0.0 (easy) to 1.0 (hard).
            target_slot: Role ID for the training candidate.
            seed: Optional RNG seed for deterministic output.
            actions: Optional pre-phase actions to execute.
            checkpoint_every_phase: Whether to checkpoint after each phase.

        Returns:
            EpisodeResult with all data.
        """
        scenario = self._catalog.generate(
            episode_type, difficulty=difficulty, target_slot=target_slot, seed=seed
        )
        return await self.run_scenario(
            scenario, actions=actions, checkpoint_every_phase=checkpoint_every_phase
        )

    async def run_scenario(
        self,
        scenario: ScenarioConfig,
        actions: Optional[List[Action]] = None,
        checkpoint_every_phase: bool = False,
    ) -> EpisodeResult:
        """Run a full episode from a ScenarioConfig.

        Args:
            scenario: Pre-generated scenario configuration.
            actions: Optional pre-phase actions to execute.
            checkpoint_every_phase: Whether to checkpoint after each phase.

        Returns:
            EpisodeResult with all data.
        """
        episode_id = f"ep-{uuid.uuid4().hex[:8]}"
        start = time.monotonic()

        # 1. Setup: build config + SprintManager
        sm = await self._setup_sprint_manager(scenario, episode_id)

        # 2. Pre-phase actions
        if actions:
            executor = ActionExecutor(sm)
            await executor.execute_batch(actions)

        # 3. Phase execution
        runner = PhaseRunner(sm)
        phase_results: List[PhaseResult] = []
        for phase in scenario.phases:
            result = await runner.run_phase(phase, sprint_num=1)
            phase_results.append(result)
            if checkpoint_every_phase:
                await self._checkpoint_mgr.save(
                    episode_id, sm, sprint_num=1, phase=phase
                )
            if result.error:
                break

        # 4. Observation
        extractor = ObservationExtractor(sm)
        final_phase = phase_results[-1].phase if phase_results else "unknown"
        obs = await extractor.extract(sprint_num=1, phase=final_phase)
        obs_dict = extractor.to_dict(obs)

        # 5. Collect decision traces
        decision_traces = self._collect_decision_traces(sm)

        # Flatten all decisions for behavioral scoring
        all_decisions: List[Dict[str, Any]] = []
        for agent_decisions in decision_traces.values():
            all_decisions.extend(agent_decisions)

        # Also collect decisions from phase results
        for pr in phase_results:
            all_decisions.extend(pr.decisions)

        # 6. Behavioral scoring
        behavioral_score, behaviors_detected = self._scorer.score(
            all_decisions, scenario.expected_behaviors
        )

        # 7. Sprint result (synthetic from phase artifacts)
        sprint_result = self._build_sprint_result(phase_results, scenario)

        # 8. Reward
        reward = self._reward.compute(
            sprint_result,
            phase_results=phase_results,
            behavioral_score=behavioral_score,
        )

        elapsed = time.monotonic() - start

        return EpisodeResult(
            episode_id=episode_id,
            episode_type=scenario.episode_type,
            stage=scenario.stage,
            difficulty=scenario.difficulty,
            phase_results=phase_results,
            final_observation=obs_dict,
            reward=reward,
            behavioral_score=behavioral_score,
            behaviors_detected=behaviors_detected,
            decision_traces=decision_traces,
            sprint_result=sprint_result,
            total_duration_seconds=elapsed,
            terminated=True,
            truncated=False,
        )

    # ── Internal helpers ─────────────────────────────────────────────

    async def _setup_sprint_manager(
        self, scenario: ScenarioConfig, episode_id: str
    ) -> Any:
        """Build a lightweight SprintManager for the episode."""
        from ..tools.shared_context import SharedContextDB
        from .backlog import Backlog
        from .sprint_manager import SprintManager

        # Build config via builder.
        # Sprint duration of 0 ensures development wall-clock loops exit
        # immediately in mock mode.  num_simulated_days=1 keeps it to a
        # single iteration.
        config = (
            ExperimentConfigBuilder()
            .name(f"episode-{episode_id}")
            .sprint_duration(0)
            .database_url("mock://")
            .tracing(True)
            .workspace(root=self._workspace_root, mode="per_story")
            .num_simulated_days(1)
            .build()
        )

        # Create mock DB
        db = SharedContextDB("mock://")
        await db.initialize()

        # Create agents
        agents = self._create_mock_agents(scenario)

        # Create backlog from scenario stories
        backlog = Backlog.from_stories(
            scenario.backlog_stories,
            product_name=f"episode-{scenario.episode_type}",
        )

        output_dir = Path(self._workspace_root) / episode_id
        output_dir.mkdir(parents=True, exist_ok=True)

        sm = SprintManager(
            agents=agents,
            shared_db=db,
            config=config,
            output_dir=output_dir,
            backlog=backlog,
        )

        return sm

    def _create_mock_agents(self, scenario: ScenarioConfig) -> List[Any]:
        """Create lightweight mock agents for the episode."""
        from ..agents.base_agent import AgentConfig, BaseAgent

        # Standard team: dev_lead, qa_lead, po, 2 developers
        agent_specs = [
            ("dev_lead", "Dev Lead", "senior", "developer", "backend"),
            ("qa_lead", "QA Lead", "senior", "tester", "testing"),
            ("po", "Product Owner", "senior", "leader", "product"),
            ("dev_mid_backend", "Dev Mid", "mid", "developer", "backend"),
            ("dev_junior_fullstack", "Dev Junior", "junior", "developer", "fullstack"),
        ]

        agents = []
        for role_id, name, seniority, archetype, spec in agent_specs:
            # Apply scenario overrides if they exist
            overrides = scenario.agent_overrides.get(role_id, {})
            cfg = AgentConfig(
                role_id=role_id,
                name=overrides.get("name", name),
                model="mock",
                temperature=0.7,
                max_tokens=4096,
                individual="",
                seniority=overrides.get("seniority", seniority),
                primary_specialization=overrides.get("primary_specialization", spec),
                role_archetype=overrides.get("role_archetype", archetype),
            )
            agent = BaseAgent(cfg, vllm_endpoint="mock://")
            agents.append(agent)

        return agents

    @staticmethod
    def _collect_decision_traces(
        sm: Any,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Collect decision traces from all agents' tracers."""
        traces: Dict[str, List[Dict[str, Any]]] = {}
        for agent in sm.agents:
            if agent._tracer is not None:
                traces[agent.agent_id] = [
                    {
                        "decision_id": d.decision_id,
                        "timestamp": d.timestamp,
                        "phase": d.phase,
                        "action_type": d.action_type,
                        "action_content": d.action_content,
                        "context": d.context,
                        "metadata": d.metadata,
                    }
                    for d in agent._tracer.decisions
                ]
        return traces

    @staticmethod
    def _build_sprint_result(
        phase_results: List[PhaseResult],
        scenario: ScenarioConfig,
    ) -> Dict[str, Any]:
        """Build a synthetic sprint result dict from phase results."""
        features_planned = len(scenario.backlog_stories)
        features_completed = 0
        pairing_sessions = 0

        for pr in phase_results:
            if pr.phase == "development" and pr.error is None:
                features_completed = pr.artifacts.get(
                    "days_completed", features_planned
                )
                pairing_sessions = pr.artifacts.get("pairing_sessions", 0)
            elif pr.phase == "qa_review" and pr.error is None:
                features_completed = pr.artifacts.get(
                    "cards_approved", features_completed
                )

        return {
            "sprint": 1,
            "velocity": features_completed * 3,
            "features_completed": features_completed,
            "features_planned": max(features_planned, 1),
            "test_coverage": 0.8 if features_completed > 0 else 0.0,
            "pairing_sessions": pairing_sessions,
        }
