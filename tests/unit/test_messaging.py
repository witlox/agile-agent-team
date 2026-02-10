"""Unit tests for the async message bus (src/agents/messaging.py)."""

import asyncio

import pytest

from src.agents.messaging import (
    InProcessBackend,
    Message,
    MessageBus,
    MessageType,
    create_message_bus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def bus() -> MessageBus:
    return create_message_bus()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_returns_queue(bus: MessageBus):
    q = bus.register("agent_a")
    assert isinstance(q, asyncio.Queue)


@pytest.mark.asyncio
async def test_register_duplicate_raises(bus: MessageBus):
    bus.register("agent_a")
    with pytest.raises(ValueError, match="already registered"):
        bus.register("agent_a")


@pytest.mark.asyncio
async def test_unregister_allows_reregister(bus: MessageBus):
    bus.register("agent_a")
    bus.unregister("agent_a")
    q = bus.register("agent_a")
    assert isinstance(q, asyncio.Queue)


# ---------------------------------------------------------------------------
# Direct messaging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_receive(bus: MessageBus):
    bus.register("alice")
    q = bus.register("bob")

    msg = await bus.send("alice", "bob", {"text": "hello"})
    assert msg.type == MessageType.DIRECT
    assert msg.sender == "alice"
    assert msg.recipients == ("bob",)

    received = q.get_nowait()
    assert received.id == msg.id
    assert received.content == {"text": "hello"}


@pytest.mark.asyncio
async def test_send_to_unregistered_raises(bus: MessageBus):
    bus.register("alice")
    with pytest.raises(ValueError, match="not registered"):
        await bus.send("alice", "ghost", {"text": "hi"})


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_and_send_to_channel(bus: MessageBus):
    q_a = bus.register("a")
    q_b = bus.register("b")
    bus.register("c")  # not in channel

    bus.create_channel("pair-1", members={"a", "b"})

    msg = await bus.send_to_channel("a", "pair-1", {"step": 1})
    assert msg.type == MessageType.CHANNEL
    assert msg.channel == "pair-1"

    # b receives, a (sender) does not
    received = q_b.get_nowait()
    assert received.content == {"step": 1}
    assert q_a.empty()


@pytest.mark.asyncio
async def test_create_duplicate_channel_raises(bus: MessageBus):
    bus.create_channel("ch")
    with pytest.raises(ValueError, match="already exists"):
        bus.create_channel("ch")


@pytest.mark.asyncio
async def test_delete_channel(bus: MessageBus):
    bus.create_channel("temp")
    bus.delete_channel("temp")
    with pytest.raises(ValueError, match="does not exist"):
        bus.delete_channel("temp")


@pytest.mark.asyncio
async def test_send_to_nonexistent_channel_raises(bus: MessageBus):
    bus.register("a")
    with pytest.raises(ValueError, match="does not exist"):
        await bus.send_to_channel("a", "nope", {"x": 1})


# ---------------------------------------------------------------------------
# Broadcast
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_delivers_to_all_except_sender(bus: MessageBus):
    q_a = bus.register("a")
    q_b = bus.register("b")
    q_c = bus.register("c")

    msg = await bus.broadcast("a", {"alert": True})
    assert msg.type == MessageType.BROADCAST
    assert set(msg.recipients) == {"b", "c"}

    assert q_a.empty() is not False or q_a.empty()  # sender excluded
    assert q_a.empty()
    assert q_b.get_nowait().content == {"alert": True}
    assert q_c.get_nowait().content == {"alert": True}


# ---------------------------------------------------------------------------
# Pub/Sub
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscribe_and_publish(bus: MessageBus):
    bus.register("pub")
    bus.register("sub1")

    received_messages = []

    async def handler(m: Message):
        received_messages.append(m)

    bus.subscribe("topic_x", "sub1", handler)

    msg = await bus.publish("pub", "topic_x", {"data": 42})
    assert msg.type == MessageType.EVENT

    assert len(received_messages) == 1
    assert received_messages[0].content == {"data": 42}


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery(bus: MessageBus):
    bus.register("pub")
    bus.register("sub")

    calls = []

    async def handler(m: Message):
        calls.append(m)

    bus.subscribe("t", "sub", handler)
    bus.unsubscribe("t", "sub")

    await bus.publish("pub", "t", {"x": 1})
    assert len(calls) == 0


# ---------------------------------------------------------------------------
# Request / Reply
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_reply_round_trip(bus: MessageBus):
    bus.register("requester")
    q_responder = bus.register("responder")

    async def responder_loop():
        req = await asyncio.wait_for(q_responder.get(), timeout=2.0)
        await bus.reply("responder", req.id, {"answer": 42})

    task = asyncio.create_task(responder_loop())

    reply = await bus.request(
        "requester", "responder", {"question": "what?"}, timeout=2.0
    )
    assert reply.type == MessageType.REPLY
    assert reply.content == {"answer": 42}

    await task


@pytest.mark.asyncio
async def test_request_timeout_raises(bus: MessageBus):
    bus.register("requester")
    bus.register("slow_responder")

    with pytest.raises(asyncio.TimeoutError):
        await bus.request("requester", "slow_responder", {"q": 1}, timeout=0.05)


@pytest.mark.asyncio
async def test_request_to_unregistered_raises(bus: MessageBus):
    bus.register("requester")
    with pytest.raises(ValueError, match="not registered"):
        await bus.request("requester", "ghost", {"q": 1}, timeout=0.1)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_history_stores_messages(bus: MessageBus):
    bus.register("a")
    bus.register("b")

    await bus.send("a", "b", {"m": 1})
    await bus.send("a", "b", {"m": 2})

    history = await bus.get_history()
    assert len(history) == 2
    assert history[0].content == {"m": 1}
    assert history[1].content == {"m": 2}


@pytest.mark.asyncio
async def test_history_channel_filter(bus: MessageBus):
    bus.register("a")
    bus.register("b")
    bus.create_channel("ch1", members={"a", "b"})

    await bus.send("a", "b", {"direct": True})
    await bus.send_to_channel("a", "ch1", {"ch": True})

    all_history = await bus.get_history()
    assert len(all_history) == 2

    ch_history = await bus.get_history(channel="ch1")
    assert len(ch_history) == 1
    assert ch_history[0].content == {"ch": True}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats(bus: MessageBus):
    bus.register("a")
    bus.register("b")
    bus.create_channel("c1", members={"a", "b"})

    await bus.send("a", "b", {"x": 1})

    s = bus.stats
    assert s["registered_agents"] == 2
    assert s["channels"] == 1
    assert s["total_messages"] == 1


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_factory_default_creates_asyncio_bus():
    bus = create_message_bus()
    assert isinstance(bus._backend, InProcessBackend)


def test_factory_with_config():
    bus = create_message_bus({"backend": "asyncio", "history_size": 500})
    assert isinstance(bus._backend, InProcessBackend)
    assert bus._backend._history_size == 500


def test_factory_redis_backend():
    bus = create_message_bus(
        {"backend": "redis", "redis_url": "redis://localhost:6379"}
    )
    from src.agents.messaging import RedisBackend

    assert isinstance(bus._backend, RedisBackend)
