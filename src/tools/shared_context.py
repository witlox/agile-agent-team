"""Shared context database for team state."""

import json
from typing import Dict, List


class SharedContextDB:
    """PostgreSQL-backed shared context database.

    When the database URL is "mock://" or asyncpg is unavailable,
    falls back to an in-memory store for local development and testing.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
        self._mock_mode = database_url == "mock://" or not database_url.startswith(
            "postgresql"
        )
        # In-memory store for mock mode
        self._cards: List[Dict] = []
        self._pairing_sessions: List[Dict] = []
        self._meta_learnings: List[Dict] = []
        self._snapshots: List[Dict] = []
        self._disturbance_events: List[Dict] = []
        self._next_id = 1

    async def initialize(self):
        """Create connection pool and initialize schema."""
        if self._mock_mode:
            return
        try:
            import asyncpg

            self.pool = await asyncpg.create_pool(self.database_url)
            await self._create_schema()
        except Exception as exc:
            raise RuntimeError(f"Failed to connect to database: {exc}") from exc

    async def _create_schema(self):
        """Create database tables."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kanban_cards (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    assigned_pair TEXT[],
                    story_points INTEGER,
                    sprint INTEGER,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS pairing_sessions (
                    id SERIAL PRIMARY KEY,
                    sprint INTEGER,
                    driver_id TEXT,
                    navigator_id TEXT,
                    task_id INTEGER,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    outcome TEXT,
                    decisions JSONB
                );

                CREATE TABLE IF NOT EXISTS meta_learnings (
                    id SERIAL PRIMARY KEY,
                    sprint INTEGER,
                    agent_id TEXT,
                    learning_type TEXT,
                    content JSONB,
                    applied BOOLEAN DEFAULT FALSE
                );

                CREATE TABLE IF NOT EXISTS kanban_snapshots (
                    id SERIAL PRIMARY KEY,
                    sprint INTEGER,
                    snapshot_data JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS disturbance_events (
                    id SERIAL PRIMARY KEY,
                    type TEXT,
                    impact TEXT,
                    affected_agents JSONB,
                    details JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """
            )

    # --- Kanban card helpers ---

    async def add_card(self, card_data: Dict) -> int:
        """Insert a new kanban card and return its id."""
        if self._mock_mode:
            card = dict(card_data)
            card["id"] = self._next_id
            card.setdefault("metadata", None)  # Initialize metadata field
            self._next_id += 1
            self._cards.append(card)
            return card["id"]
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO kanban_cards
                   (title, description, status, assigned_pair, story_points, sprint, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   RETURNING id""",
                card_data.get("title", ""),
                card_data.get("description", ""),
                card_data.get("status", "ready"),
                card_data.get("assigned_pair", []),
                card_data.get("story_points", 1),
                card_data.get("sprint", 0),
                card_data.get("metadata"),
            )
            return row["id"]

    async def get_cards_by_status(self, status: str) -> List[Dict]:
        """Return all cards with the given status."""
        if self._mock_mode:
            return [c for c in self._cards if c.get("status") == status]
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM kanban_cards WHERE status = $1 ORDER BY id", status
            )
            return [dict(r) for r in rows]

    async def get_wip_count(self, status: str) -> int:
        """Return the number of cards currently in the given status column."""
        if self._mock_mode:
            return sum(1 for c in self._cards if c.get("status") == status)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT COUNT(*) AS cnt FROM kanban_cards WHERE status = $1", status
            )
            return row["cnt"]

    async def update_card_status(self, card_id: int, status: str):
        """Update the status of a kanban card."""
        if self._mock_mode:
            for card in self._cards:
                if card["id"] == card_id:
                    card["status"] = status
                    return
            raise ValueError(f"Card {card_id} not found")
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE kanban_cards SET status = $1 WHERE id = $2", status, card_id
            )

    # --- Snapshot / pairing helpers ---

    async def save_kanban_snapshot(self, sprint: int, data: Dict):
        """Save Kanban board state."""
        if self._mock_mode:
            self._snapshots.append({"sprint": sprint, "data": data})
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO kanban_snapshots (sprint, snapshot_data) VALUES ($1, $2)",
                sprint,
                json.dumps(data),
            )

    async def log_pairing_session(self, session_data: Dict):
        """Log a pairing session."""
        if self._mock_mode:
            self._pairing_sessions.append(session_data)
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO pairing_sessions
                   (sprint, driver_id, navigator_id, task_id, start_time, end_time, outcome, decisions)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                session_data.get("sprint"),
                session_data.get("driver_id"),
                session_data.get("navigator_id"),
                session_data.get("task_id"),
                session_data.get("start_time"),
                session_data.get("end_time"),
                session_data.get("outcome"),
                json.dumps(session_data.get("decisions", {})),
            )

    async def get_pairing_sessions_for_sprint(self, sprint: int) -> List[Dict]:
        """Return all pairing sessions for a given sprint."""
        if self._mock_mode:
            return [s for s in self._pairing_sessions if s.get("sprint") == sprint]
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM pairing_sessions WHERE sprint = $1", sprint
            )
            return [dict(r) for r in rows]

    async def update_card_field(self, card_id: int, field: str, value: str):
        """Update a single text field on a kanban card."""
        if self._mock_mode:
            for card in self._cards:
                if card["id"] == card_id:
                    card[field] = value
                    return
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE kanban_cards SET {field} = $1 WHERE id = $2", value, card_id
            )

    async def log_disturbance(self, event: Dict):
        """Log a disturbance event."""
        if self._mock_mode:
            self._disturbance_events.append(event)
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO disturbance_events (type, impact, affected_agents, details)
                   VALUES ($1, $2, $3, $4)""",
                event.get("type"),
                event.get("impact"),
                json.dumps(event.get("affected_agents", [])),
                json.dumps(
                    {
                        k: v
                        for k, v in event.items()
                        if k not in ("type", "impact", "affected_agents")
                    }
                ),
            )

    async def get_disturbance_events(self) -> List[Dict]:
        """Return all logged disturbance events."""
        if self._mock_mode:
            return list(self._disturbance_events)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM disturbance_events ORDER BY id")
            return [dict(r) for r in rows]

    async def close(self):
        """Close the connection pool."""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
