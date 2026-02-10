"""Integration tests for message bus with BaseAgent."""

import asyncio
import os

import pytest

from src.agents.base_agent import BaseAgent, AgentConfig
from src.agents.messaging import MessageType, create_message_bus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(role_id: str = "dev_a") -> BaseAgent:
    """Create a minimal BaseAgent in mock mode."""
    os.environ["MOCK_LLM"] = "true"
    config = AgentConfig(
        role_id=role_id,
        name=f"Test Agent ({role_id})",
        model="mock",
        temperature=0.7,
        max_tokens=256,
        seniority="mid",
        role_archetype="developer",
    )
    return BaseAgent(config, vllm_endpoint="mock://")


# ---------------------------------------------------------------------------
# agent_id property
# ---------------------------------------------------------------------------


def test_agent_id_property():
    agent = _make_agent("my_role")
    assert agent.agent_id == "my_role"
    assert agent.agent_id == agent.config.role_id


# ---------------------------------------------------------------------------
# Agent send / receive via convenience methods
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_send_receive():
    bus = create_message_bus()
    alice = _make_agent("alice")
    bob = _make_agent("bob")

    alice.attach_message_bus(bus)
    bob.attach_message_bus(bus)

    msg = await alice.send_message("bob", {"greeting": "hi"})
    assert msg is not None
    assert msg.type == MessageType.DIRECT

    received = await bob.receive_message()
    assert received is not None
    assert received.content == {"greeting": "hi"}


# ---------------------------------------------------------------------------
# Agent request / reply
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_request_reply():
    bus = create_message_bus()
    requester = _make_agent("requester")
    responder = _make_agent("responder")

    requester.attach_message_bus(bus)
    responder.attach_message_bus(bus)

    async def respond():
        msg = await asyncio.wait_for(responder.inbox.get(), timeout=2.0)
        await bus.reply("responder", msg.id, {"answer": "yes"})

    task = asyncio.create_task(respond())

    reply = await requester.request_from(
        "responder", {"question": "ready?"}, timeout=2.0
    )
    assert reply is not None
    assert reply.content == {"answer": "yes"}

    await task


# ---------------------------------------------------------------------------
# Agent subscribe topic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_subscribe_topic():
    bus = create_message_bus()
    publisher = _make_agent("publisher")
    subscriber = _make_agent("subscriber")

    publisher.attach_message_bus(bus)
    subscriber.attach_message_bus(bus)

    events = []

    async def handler(m):
        events.append(m)

    subscriber.subscribe_topic("updates", handler)

    await bus.publish("publisher", "updates", {"version": 2})

    assert len(events) == 1
    assert events[0].content == {"version": 2}


# ---------------------------------------------------------------------------
# Agent without bus returns None gracefully
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_without_bus_returns_none():
    agent = _make_agent("lonely")
    assert agent.message_bus is None
    assert agent.inbox is None

    result = await agent.send_message("nobody", {"x": 1})
    assert result is None

    result = await agent.receive_message()
    assert result is None

    result = await agent.request_from("nobody", {"q": 1}, timeout=0.01)
    assert result is None

    # subscribe_topic should be a no-op (no error)
    agent.subscribe_topic("t", lambda m: None)
