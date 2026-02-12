"""Unit tests for the pluggable runtime registry (F-06)."""

import pytest

from src.agents.runtime.factory import (
    _RUNTIME_REGISTRY,
    _default_registrations,
    create_runtime,
    get_runtime_config,
    register_runtime,
    registered_runtime_types,
)
from src.agents.runtime.base import AgentRuntime


class _DummyRuntime(AgentRuntime):
    """Minimal runtime for testing the registry."""

    def __init__(self, config, tools):
        super().__init__(config, tools)
        self.initialized = True

    async def execute_task(self, system_prompt, user_message, max_turns=20):
        from src.agents.runtime.base import RuntimeResult

        return RuntimeResult(content="dummy", tool_calls=[], success=True)


class TestDefaultRegistrations:
    def test_defaults_include_builtins(self):
        _default_registrations()
        types = registered_runtime_types()
        assert "local_vllm" in types
        assert "anthropic" in types


class TestRegisterRuntime:
    def test_register_custom_type(self):
        register_runtime("test_custom", lambda cfg, tools: _DummyRuntime(cfg, tools))
        assert "test_custom" in registered_runtime_types()
        # Cleanup
        _RUNTIME_REGISTRY.pop("test_custom", None)

    def test_re_registration_overwrites(self):
        sentinel = object()
        register_runtime("test_overwrite", lambda cfg, tools: sentinel)  # type: ignore[arg-type]
        register_runtime("test_overwrite", lambda cfg, tools: _DummyRuntime(cfg, tools))
        # Factory should use the latest registration
        fn = _RUNTIME_REGISTRY["test_overwrite"]
        result = fn({}, [])
        assert isinstance(result, _DummyRuntime)
        _RUNTIME_REGISTRY.pop("test_overwrite", None)


class TestCreateRuntime:
    def test_create_with_custom_type(self):
        register_runtime("test_create", lambda cfg, tools: _DummyRuntime(cfg, tools))
        runtime = create_runtime(
            "test_create",
            runtime_config={"key": "value"},
            tool_names=[],
            workspace_root="/tmp",
        )
        assert isinstance(runtime, _DummyRuntime)
        assert runtime.config == {"key": "value"}
        assert runtime.initialized is True
        _RUNTIME_REGISTRY.pop("test_create", None)

    def test_create_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown runtime type"):
            create_runtime(
                "nonexistent_runtime",
                runtime_config={},
                tool_names=[],
                workspace_root="/tmp",
            )

    def test_error_message_lists_available(self):
        try:
            create_runtime("bad", {}, [], "/tmp")
        except ValueError as e:
            msg = str(e)
            assert "Available:" in msg
            assert "local_vllm" in msg
            assert "anthropic" in msg

    def test_custom_factory_receives_args(self):
        received = {}

        def capture_factory(cfg, tools):
            received["config"] = cfg
            received["tools"] = tools
            return _DummyRuntime(cfg, tools)

        register_runtime("test_capture", capture_factory)
        create_runtime(
            "test_capture",
            runtime_config={"model": "test-model"},
            tool_names=[],
            workspace_root="/tmp",
        )
        assert received["config"] == {"model": "test-model"}
        assert isinstance(received["tools"], list)
        _RUNTIME_REGISTRY.pop("test_capture", None)


class TestGetRuntimeConfig:
    def test_validates_against_registry(self):
        _default_registrations()
        agent_config = {"runtime": "nonexistent"}
        with pytest.raises(ValueError, match="Unknown runtime type"):
            get_runtime_config(agent_config, {})

    def test_returns_correct_type(self):
        _default_registrations()
        agent_config = {"runtime": "anthropic", "model": "claude-test"}
        runtime_type, config = get_runtime_config(
            agent_config, {"anthropic": {"default_model": "claude-3"}}
        )
        assert runtime_type == "anthropic"
        assert config["model"] == "claude-test"

    def test_custom_type_in_agent_config(self):
        register_runtime("test_agent_cfg", lambda cfg, tools: _DummyRuntime(cfg, tools))
        agent_config = {"runtime": "test_agent_cfg"}
        runtime_type, config = get_runtime_config(agent_config, {})
        assert runtime_type == "test_agent_cfg"
        _RUNTIME_REGISTRY.pop("test_agent_cfg", None)
