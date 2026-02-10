"""Async message bus for peer-to-peer agent communication.

Supports direct messages, channels, broadcast, pub/sub topics, and
request/reply — enabling agents to form ad-hoc constellations (pairs,
standup groups, incident teams) and communicate directly without
orchestrator mediation.

Two backends:
- InProcessBackend: Pure asyncio, zero-dependency (default)
- RedisBackend: For multi-process scaling (redis already in requirements.txt)
"""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class MessageType(Enum):
    """Type of message being sent."""

    DIRECT = "direct"
    CHANNEL = "channel"
    BROADCAST = "broadcast"
    REQUEST = "request"
    REPLY = "reply"
    EVENT = "event"


@dataclass(frozen=True)
class Message:
    """Immutable message passed between agents.

    Frozen for safe concurrent access by multiple coroutines.
    """

    id: str
    sender: str
    recipients: Tuple[str, ...]
    type: MessageType
    content: Dict[str, Any]
    timestamp: datetime
    channel: Optional[str] = None
    reply_to: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Channel:
    """Named communication channel with a fixed set of members."""

    name: str
    members: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


# Callable type for message handlers (pub/sub)
MessageHandler = Callable[[Message], Awaitable[None]]


# ---------------------------------------------------------------------------
# Backend abstraction (Strategy pattern)
# ---------------------------------------------------------------------------


class MessageBackend(ABC):
    """Abstract backend for message storage and delivery."""

    @abstractmethod
    async def deliver(self, inbox_id: str, message: Message) -> None:
        """Deliver a message to an agent's inbox."""

    @abstractmethod
    async def store(self, message: Message) -> None:
        """Store a message in history."""

    @abstractmethod
    async def get_history(
        self,
        limit: int = 100,
        channel: Optional[str] = None,
    ) -> List[Message]:
        """Retrieve message history, optionally filtered by channel."""


class InProcessBackend(MessageBackend):
    """In-memory backend using asyncio queues. Zero external dependencies."""

    def __init__(
        self,
        inboxes: Dict[str, asyncio.Queue],  # type: ignore[type-arg]
        history_size: int = 1000,
    ) -> None:
        self._inboxes = inboxes
        self._history: List[Message] = []
        self._history_size = history_size

    async def deliver(self, inbox_id: str, message: Message) -> None:
        queue = self._inboxes.get(inbox_id)
        if queue is not None:
            queue.put_nowait(message)

    async def store(self, message: Message) -> None:
        self._history.append(message)
        # Trim to bounded size
        if len(self._history) > self._history_size:
            self._history = self._history[-self._history_size :]

    async def get_history(
        self,
        limit: int = 100,
        channel: Optional[str] = None,
    ) -> List[Message]:
        source = self._history
        if channel is not None:
            source = [m for m in source if m.channel == channel]
        return source[-limit:]


class RedisBackend(MessageBackend):
    """Redis-backed message backend for multi-process scaling.

    Uses ``redis.asyncio`` (redis==5.0.1, already in requirements.txt).
    Messages are JSON-serialised and stored in a bounded list.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        history_size: int = 1000,
        inboxes: Optional[Dict[str, asyncio.Queue]] = None,  # type: ignore[type-arg]
    ) -> None:
        self._redis_url = redis_url
        self._history_size = history_size
        self._inboxes = inboxes or {}
        self._redis = None  # type: ignore[assignment]

    async def _ensure_connection(self) -> Any:
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url)
        return self._redis

    @staticmethod
    def _serialise(message: Message) -> str:
        return json.dumps(
            {
                "id": message.id,
                "sender": message.sender,
                "recipients": list(message.recipients),
                "type": message.type.value,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "channel": message.channel,
                "reply_to": message.reply_to,
                "metadata": message.metadata,
            }
        )

    @staticmethod
    def _deserialise(raw: str) -> Message:
        d = json.loads(raw)
        return Message(
            id=d["id"],
            sender=d["sender"],
            recipients=tuple(d["recipients"]),
            type=MessageType(d["type"]),
            content=d["content"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            channel=d.get("channel"),
            reply_to=d.get("reply_to"),
            metadata=d.get("metadata", {}),
        )

    async def deliver(self, inbox_id: str, message: Message) -> None:
        # In-process delivery for co-located agents
        queue = self._inboxes.get(inbox_id)
        if queue is not None:
            queue.put_nowait(message)
        # Also store in Redis inbox list for cross-process consumers
        r = await self._ensure_connection()
        key = f"inbox:{inbox_id}"
        await r.lpush(key, self._serialise(message))
        await r.ltrim(key, 0, self._history_size - 1)

    async def store(self, message: Message) -> None:
        r = await self._ensure_connection()
        key = "messages:history"
        if message.channel:
            key = f"messages:channel:{message.channel}"
        await r.lpush(key, self._serialise(message))
        await r.ltrim(key, 0, self._history_size - 1)

    async def get_history(
        self,
        limit: int = 100,
        channel: Optional[str] = None,
    ) -> List[Message]:
        r = await self._ensure_connection()
        key = f"messages:channel:{channel}" if channel else "messages:history"
        raw_list = await r.lrange(key, 0, limit - 1)
        return [self._deserialise(raw) for raw in reversed(raw_list)]


# ---------------------------------------------------------------------------
# MessageBus
# ---------------------------------------------------------------------------


class MessageBus:
    """Central message bus for agent-to-agent communication.

    Provides:
    - Direct 1-to-1 messaging
    - Named channels (group communication)
    - Broadcast (all agents except sender)
    - Pub/Sub topics with handler callbacks
    - Request/Reply with timeout
    - History and stats
    """

    def __init__(
        self,
        backend: Optional[MessageBackend] = None,
        history_size: int = 1000,
    ) -> None:
        self._inboxes: Dict[str, asyncio.Queue] = {}  # type: ignore[type-arg]
        self._channels: Dict[str, Channel] = {}
        self._subscriptions: Dict[str, List[Tuple[str, MessageHandler]]] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}  # type: ignore[type-arg]
        self._message_count: int = 0

        # Default to in-process backend
        if backend is None:
            backend = InProcessBackend(self._inboxes, history_size)
        self._backend = backend

        # Share inbox dict with in-process backends
        if isinstance(backend, InProcessBackend):
            backend._inboxes = self._inboxes
        elif isinstance(backend, RedisBackend):
            backend._inboxes = self._inboxes

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, role_id: str) -> asyncio.Queue:  # type: ignore[type-arg]
        """Register an agent and return its inbox queue.

        Raises ValueError if already registered.
        """
        if role_id in self._inboxes:
            raise ValueError(f"Agent '{role_id}' is already registered")
        queue: asyncio.Queue = asyncio.Queue()  # type: ignore[type-arg]
        self._inboxes[role_id] = queue
        return queue

    def unregister(self, role_id: str) -> None:
        """Remove an agent from the bus."""
        self._inboxes.pop(role_id, None)
        # Remove from all channels
        for ch in self._channels.values():
            ch.members.discard(role_id)
        # Remove subscriptions
        for topic, subs in list(self._subscriptions.items()):
            self._subscriptions[topic] = [(rid, h) for rid, h in subs if rid != role_id]

    # ------------------------------------------------------------------
    # Direct messaging
    # ------------------------------------------------------------------

    async def send(
        self,
        sender: str,
        recipient: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Send a direct message from *sender* to *recipient*.

        Raises ValueError if recipient is not registered.
        """
        if recipient not in self._inboxes:
            raise ValueError(f"Recipient '{recipient}' is not registered")

        msg = Message(
            id=str(uuid.uuid4()),
            sender=sender,
            recipients=(recipient,),
            type=MessageType.DIRECT,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )
        await self._backend.deliver(recipient, msg)
        await self._backend.store(msg)
        self._message_count += 1
        return msg

    # ------------------------------------------------------------------
    # Channels
    # ------------------------------------------------------------------

    def create_channel(
        self,
        name: str,
        members: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Channel:
        """Create a named channel. Raises ValueError if already exists."""
        if name in self._channels:
            raise ValueError(f"Channel '{name}' already exists")
        ch = Channel(name=name, members=members or set(), metadata=metadata or {})
        self._channels[name] = ch
        return ch

    def delete_channel(self, name: str) -> None:
        """Delete a channel. Raises ValueError if not found."""
        if name not in self._channels:
            raise ValueError(f"Channel '{name}' does not exist")
        del self._channels[name]

    async def send_to_channel(
        self,
        sender: str,
        channel_name: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Send a message to all members of a channel (except sender).

        Raises ValueError if channel does not exist.
        """
        ch = self._channels.get(channel_name)
        if ch is None:
            raise ValueError(f"Channel '{channel_name}' does not exist")

        recipients = tuple(m for m in ch.members if m != sender)
        msg = Message(
            id=str(uuid.uuid4()),
            sender=sender,
            recipients=recipients,
            type=MessageType.CHANNEL,
            content=content,
            timestamp=datetime.utcnow(),
            channel=channel_name,
            metadata=metadata or {},
        )
        for r in recipients:
            await self._backend.deliver(r, msg)
        await self._backend.store(msg)
        self._message_count += 1
        return msg

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def broadcast(
        self,
        sender: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Broadcast to all registered agents except sender."""
        recipients = tuple(rid for rid in self._inboxes if rid != sender)
        msg = Message(
            id=str(uuid.uuid4()),
            sender=sender,
            recipients=recipients,
            type=MessageType.BROADCAST,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )
        for r in recipients:
            await self._backend.deliver(r, msg)
        await self._backend.store(msg)
        self._message_count += 1
        return msg

    # ------------------------------------------------------------------
    # Pub/Sub
    # ------------------------------------------------------------------

    def subscribe(self, topic: str, role_id: str, handler: MessageHandler) -> None:
        """Subscribe *role_id* to *topic* with *handler* callback."""
        self._subscriptions.setdefault(topic, []).append((role_id, handler))

    def unsubscribe(self, topic: str, role_id: str) -> None:
        """Remove all handlers for *role_id* on *topic*."""
        if topic in self._subscriptions:
            self._subscriptions[topic] = [
                (rid, h) for rid, h in self._subscriptions[topic] if rid != role_id
            ]

    async def publish(
        self,
        sender: str,
        topic: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Publish an event to *topic*, firing all subscriber handlers."""
        subs = self._subscriptions.get(topic, [])
        recipients = tuple(rid for rid, _ in subs)
        msg = Message(
            id=str(uuid.uuid4()),
            sender=sender,
            recipients=recipients,
            type=MessageType.EVENT,
            content=content,
            timestamp=datetime.utcnow(),
            channel=topic,
            metadata=metadata or {},
        )

        # Fire handlers concurrently
        if subs:
            await asyncio.gather(*(handler(msg) for _, handler in subs))

        await self._backend.store(msg)
        self._message_count += 1
        return msg

    # ------------------------------------------------------------------
    # Request / Reply
    # ------------------------------------------------------------------

    async def request(
        self,
        sender: str,
        recipient: str,
        content: Dict[str, Any],
        timeout: float = 30.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Send a request and wait for a reply (with timeout).

        Returns the reply Message.
        Raises asyncio.TimeoutError if no reply within *timeout* seconds.
        Raises ValueError if recipient is not registered.
        """
        if recipient not in self._inboxes:
            raise ValueError(f"Recipient '{recipient}' is not registered")

        msg = Message(
            id=str(uuid.uuid4()),
            sender=sender,
            recipients=(recipient,),
            type=MessageType.REQUEST,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()  # type: ignore[type-arg]
        self._pending_requests[msg.id] = future

        await self._backend.deliver(recipient, msg)
        await self._backend.store(msg)
        self._message_count += 1

        try:
            reply = await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending_requests.pop(msg.id, None)

        return reply

    async def reply(
        self,
        sender: str,
        original_message_id: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Message]:
        """Reply to a request, resolving the caller's future.

        Returns the reply Message, or None if the original request is unknown.
        """
        future = self._pending_requests.get(original_message_id)
        if future is None:
            return None

        msg = Message(
            id=str(uuid.uuid4()),
            sender=sender,
            recipients=(),
            type=MessageType.REPLY,
            content=content,
            timestamp=datetime.utcnow(),
            reply_to=original_message_id,
            metadata=metadata or {},
        )

        if not future.done():
            future.set_result(msg)

        await self._backend.store(msg)
        self._message_count += 1
        return msg

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    async def get_history(
        self,
        limit: int = 100,
        channel: Optional[str] = None,
    ) -> List[Message]:
        """Return recent message history."""
        return await self._backend.get_history(limit=limit, channel=channel)

    @property
    def stats(self) -> Dict[str, int]:
        """Return bus statistics."""
        return {
            "registered_agents": len(self._inboxes),
            "channels": len(self._channels),
            "total_messages": self._message_count,
            "pending_requests": len(self._pending_requests),
            "subscriptions": sum(len(subs) for subs in self._subscriptions.values()),
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_message_bus(config: Optional[Dict[str, Any]] = None) -> MessageBus:
    """Create a MessageBus from configuration dict.

    Config keys:
        backend: "asyncio" (default) | "redis"
        redis_url: str (default "redis://localhost:6379")
        history_size: int (default 1000)
    """
    config = config or {}
    backend_type = config.get("backend", "asyncio")
    history_size = int(config.get("history_size", 1000))

    if backend_type == "redis":
        redis_url = config.get("redis_url", "redis://localhost:6379")
        backend: MessageBackend = RedisBackend(
            redis_url=redis_url, history_size=history_size
        )
    else:
        # InProcessBackend — inbox dict will be assigned by MessageBus.__init__
        backend = InProcessBackend(inboxes={}, history_size=history_size)

    return MessageBus(backend=backend, history_size=history_size)
