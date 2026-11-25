"""State backend for gateway session + loop-detection state.

The gateway tracks, per API key, its active sessions and, per session, a short
history of prompt hashes for loop detection. This lives in process memory —
correct for a single worker; the idle-timeout and loop-detection *semantics*
stay in the gateway service, this module only persists and retrieves raw
state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Optional


class StateStore(ABC):
    """Storage primitives for gateway sessions and loop histories."""

    # ── sessions ──
    @abstractmethod
    def get_session(self, key_hash: str, session_id: str) -> Optional[dict]: ...

    @abstractmethod
    def all_sessions(self, key_hash: str) -> dict[str, dict]: ...

    @abstractmethod
    def put_session(self, key_hash: str, session_id: str, data: dict) -> None: ...

    @abstractmethod
    def delete_session(self, key_hash: str, session_id: str) -> None: ...

    @abstractmethod
    def get_default_session_id(self, key_hash: str) -> Optional[str]: ...

    @abstractmethod
    def set_default_session_id(self, key_hash: str, session_id: str) -> None: ...

    @abstractmethod
    def delete_default_session_id(self, key_hash: str) -> None: ...

    # ── loop histories ──
    @abstractmethod
    def append_loop(self, storage_key: str, value: str, max_len: int) -> list[str]:
        """Append ``value``, trim to the most recent ``max_len``, return the list."""

    @abstractmethod
    def clear_loop(self, storage_key: str) -> None: ...

    # ── usage counters (hot-path enforcement without per-request DB scans) ──
    @abstractmethod
    def get_counter(self, key: str) -> Optional[float]:
        """Return the counter's value, or None if it has never been set."""

    @abstractmethod
    def set_counter(self, key: str, value: float) -> None: ...

    @abstractmethod
    def add_counter(self, key: str, delta: float) -> float:
        """Add ``delta`` to an existing counter and return the new value."""

    @abstractmethod
    def delete_counter(self, key: str) -> None: ...

    @abstractmethod
    def has_events(self, key: str) -> bool:
        """Whether an event window has been started for ``key``."""

    @abstractmethod
    def seed_events(self, key: str, timestamps: list[float]) -> None: ...

    @abstractmethod
    def add_event(self, key: str, ts: float) -> None: ...

    @abstractmethod
    def count_events_since(self, key: str, since: float) -> int:
        """Count events at or after ``since`` and drop the older ones."""

    # ── util ──
    @abstractmethod
    def reset(self) -> None:
        """Drop all state (used by tests)."""


class InMemoryStateStore(StateStore):
    """Process-local store (single-worker default)."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, dict]] = defaultdict(dict)
        self._default_session_ids: dict[str, str] = {}
        self._histories: dict[str, list[str]] = defaultdict(list)
        self._counters: dict[str, float] = {}
        self._events: dict[str, deque[float]] = {}

    def get_session(self, key_hash, session_id):
        return self._sessions.get(key_hash, {}).get(session_id)

    def all_sessions(self, key_hash):
        return dict(self._sessions.get(key_hash, {}))

    def put_session(self, key_hash, session_id, data):
        self._sessions[key_hash][session_id] = dict(data)

    def delete_session(self, key_hash, session_id):
        self._sessions.get(key_hash, {}).pop(session_id, None)

    def get_default_session_id(self, key_hash):
        return self._default_session_ids.get(key_hash)

    def set_default_session_id(self, key_hash, session_id):
        self._default_session_ids[key_hash] = session_id

    def delete_default_session_id(self, key_hash):
        self._default_session_ids.pop(key_hash, None)

    def append_loop(self, storage_key, value, max_len):
        history = self._histories[storage_key]
        history.append(value)
        if len(history) > max_len:
            del history[:-max_len]
        return list(history)

    def clear_loop(self, storage_key):
        self._histories.pop(storage_key, None)

    def get_counter(self, key):
        return self._counters.get(key)

    def set_counter(self, key, value):
        self._counters[key] = value

    def add_counter(self, key, delta):
        self._counters[key] = self._counters.get(key, 0.0) + delta
        return self._counters[key]

    def delete_counter(self, key):
        self._counters.pop(key, None)

    def has_events(self, key):
        return key in self._events

    def seed_events(self, key, timestamps):
        self._events[key] = deque(sorted(timestamps))

    def add_event(self, key, ts):
        self._events.setdefault(key, deque()).append(ts)

    def count_events_since(self, key, since):
        events = self._events.get(key)
        if not events:
            return 0
        while events and events[0] < since:
            events.popleft()
        return len(events)

    def reset(self):
        self._sessions.clear()
        self._default_session_ids.clear()
        self._histories.clear()
        self._counters.clear()
        self._events.clear()


def build_state_store() -> StateStore:
    """Build the gateway's state store (in-memory, single-worker)."""
    return InMemoryStateStore()
