"""Unit tests for the decision tracer (F-03, F-04)."""

import json

from src.agents.decision_tracer import Decision, DecisionTracer


class TestDecisionIdFormat:
    """Decision ID format: {agent_id}-s{sprint:02d}-{phase}-{seq:03d}"""

    def test_first_id_in_phase(self):
        tracer = DecisionTracer("alex_dev", 3)
        tracer.set_phase("planning")
        did = tracer.next_decision_id()
        assert did == "alex_dev-s03-planning-001"

    def test_sequential_ids_within_phase(self):
        tracer = DecisionTracer("alex_dev", 1)
        tracer.set_phase("development")
        ids = [tracer.next_decision_id() for _ in range(3)]
        assert ids == [
            "alex_dev-s01-development-001",
            "alex_dev-s01-development-002",
            "alex_dev-s01-development-003",
        ]

    def test_phase_change_resets_sequence(self):
        tracer = DecisionTracer("ahmed", 5)
        tracer.set_phase("planning")
        tracer.next_decision_id()
        tracer.next_decision_id()

        tracer.set_phase("development")
        did = tracer.next_decision_id()
        assert did == "ahmed-s05-development-001"

    def test_sprint_number_zero_padded(self):
        tracer = DecisionTracer("agent_x", 1)
        tracer.set_phase("retro")
        assert tracer.next_decision_id() == "agent_x-s01-retro-001"

    def test_sprint_number_two_digits(self):
        tracer = DecisionTracer("agent_x", 15)
        tracer.set_phase("qa_review")
        assert tracer.next_decision_id() == "agent_x-s15-qa_review-001"

    def test_unknown_phase_default(self):
        tracer = DecisionTracer("agent_x", 1)
        # Default phase is "unknown"
        did = tracer.next_decision_id()
        assert did == "agent_x-s01-unknown-001"


class TestDecisionRecord:
    def test_record_appends_to_list(self):
        tracer = DecisionTracer("alex", 1)
        tracer.set_phase("planning")
        d = Decision(
            decision_id="alex-s01-planning-001",
            timestamp="2026-02-08T14:00:00Z",
            phase="planning",
            context="Sprint 1 planning",
            action_type="generate",
            action_content="Selected US-001",
            reasoning_trace="Full reasoning...",
        )
        tracer.record(d)
        assert len(tracer.decisions) == 1
        assert tracer.decisions[0].decision_id == "alex-s01-planning-001"

    def test_record_from_generate(self):
        tracer = DecisionTracer("alex", 2)
        tracer.set_phase("retro")
        did = tracer.record_from_generate(
            context="Sprint 2 retro prompt",
            response="KEEP: Good pairing",
        )
        assert did == "alex-s02-retro-001"
        assert len(tracer.decisions) == 1
        assert tracer.decisions[0].action_type == "generate"

    def test_record_from_coding_task(self):
        tracer = DecisionTracer("dev", 1)
        tracer.set_phase("development")
        result = {
            "content": "Implemented feature X",
            "files_changed": ["src/foo.py"],
            "tool_calls": ["write_file", "run_tests"],
            "turns": 5,
            "success": True,
        }
        did = tracer.record_from_coding_task("Implement feature X", result)
        assert did == "dev-s01-development-001"
        d = tracer.decisions[0]
        assert d.action_type == "execute_coding_task"
        assert d.metadata["files_changed"] == ["src/foo.py"]
        assert d.metadata["success"] is True

    def test_context_truncated_at_500(self):
        tracer = DecisionTracer("agent", 1)
        tracer.set_phase("dev")
        long_context = "x" * 1000
        tracer.record_from_generate(long_context, "ok")
        assert len(tracer.decisions[0].context) == 500

    def test_action_content_truncated_at_1000(self):
        tracer = DecisionTracer("agent", 1)
        tracer.set_phase("dev")
        long_response = "y" * 2000
        tracer.record_from_generate("prompt", long_response)
        assert len(tracer.decisions[0].action_content) == 1000

    def test_last_decision_id_empty_when_no_decisions(self):
        tracer = DecisionTracer("agent", 1)
        assert tracer.last_decision_id == ""

    def test_last_decision_id_returns_most_recent(self):
        tracer = DecisionTracer("agent", 1)
        tracer.set_phase("dev")
        tracer.record_from_generate("a", "b")
        tracer.record_from_generate("c", "d")
        assert tracer.last_decision_id == "agent-s01-dev-002"


class TestSerialization:
    def test_to_dict_structure(self):
        tracer = DecisionTracer("ahmed", 3)
        tracer.set_phase("planning")
        tracer.record_from_generate("context", "response")
        data = tracer.to_dict()

        assert data["agent_id"] == "ahmed"
        assert data["sprint"] == 3
        assert len(data["decisions"]) == 1
        d = data["decisions"][0]
        assert d["decision_id"] == "ahmed-s03-planning-001"
        assert d["phase"] == "planning"
        assert d["action_type"] == "generate"
        assert d["outcome"] is None

    def test_to_dict_empty_decisions(self):
        tracer = DecisionTracer("agent", 1)
        data = tracer.to_dict()
        assert data["decisions"] == []

    def test_write_trace_creates_file(self, tmp_path):
        tracer = DecisionTracer("alex", 1)
        tracer.set_phase("dev")
        tracer.record_from_generate("prompt", "response")

        tracer.write_trace(tmp_path / "traces")
        path = tmp_path / "traces" / "alex.json"
        assert path.exists()

        data = json.loads(path.read_text())
        assert data["agent_id"] == "alex"
        assert len(data["decisions"]) == 1

    def test_write_trace_creates_directory(self, tmp_path):
        tracer = DecisionTracer("agent", 2)
        traces_dir = tmp_path / "nested" / "traces"
        tracer.write_trace(traces_dir)
        assert (traces_dir / "agent.json").exists()


class TestPhaseTransitions:
    def test_set_phase_updates_current_phase(self):
        tracer = DecisionTracer("agent", 1)
        assert tracer.current_phase == "unknown"
        tracer.set_phase("planning")
        assert tracer.current_phase == "planning"
        tracer.set_phase("development")
        assert tracer.current_phase == "development"

    def test_decisions_track_correct_phase(self):
        tracer = DecisionTracer("agent", 1)
        tracer.set_phase("planning")
        tracer.record_from_generate("a", "b")
        tracer.set_phase("development")
        tracer.record_from_generate("c", "d")

        assert tracer.decisions[0].phase == "planning"
        assert tracer.decisions[1].phase == "development"
