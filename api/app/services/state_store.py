"""Pluggable state backend for gateway session + loop-detection state.

The gateway tracks, per API key, its active sessions and, per session, a short
history of prompt hashes for loop detection. By default this lives in process
memory — correct for a single worker, but lost on restart and not shared across
workers. Set ``REDIS_URL`` to back it with Redis so multiple workers/replicas
share the state and it survives restarts.

The idle-timeout and loop-detection *semantics* stay in the gateway service;
this module only persists and retrieves raw state, so both backends behave
identically (verified with fakeredis in api/tests/test_gateway_state.py).
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Optional

logger = logging.getLogger("steerplane")


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

    def reset(self):
        self._sessions.clear()
        self._default_session_ids.clear()
        self._histories.clear()


class RedisStateStore(StateStore):
    """Redis-backed store for multi-worker / restart-safe gateway state."""

    def __init__(self, client, prefix: str = "sp:gw:") -> None:
        self._r = client
        self._p = prefix

    def _skey(self, key_hash: str) -> str:
        return f"{self._p}sessions:{key_hash}"

    def _dkey(self, key_hash: str) -> str:
        return f"{self._p}default:{key_hash}"

    def _lkey(self, storage_key: str) -> str:
        return f"{self._p}loop:{storage_key}"

    def get_session(self, key_hash, session_id):
        raw = self._r.hget(self._skey(key_hash), session_id)
        return json.loads(raw) if raw else None

    def all_sessions(self, key_hash):
        return {sid: json.loads(raw) for sid, raw in self._r.hgetall(self._skey(key_hash)).items()}

    def put_session(self, key_hash, session_id, data):
        self._r.hset(self._skey(key_hash), session_id, json.dumps(data))

    def delete_session(self, key_hash, session_id):
        self._r.hdel(self._skey(key_hash), session_id)

    def get_default_session_id(self, key_hash):
        return self._r.get(self._dkey(key_hash))

    def set_default_session_id(self, key_hash, session_id):
        self._r.set(self._dkey(key_hash), session_id)

    def delete_default_session_id(self, key_hash):
        self._r.delete(self._dkey(key_hash))

    def append_loop(self, storage_key, value, max_len):
        key = self._lkey(storage_key)
        pipe = self._r.pipeline()
        pipe.rpush(key, value)
        pipe.ltrim(key, -max_len, -1)
        pipe.lrange(key, 0, -1)
        return pipe.execute()[-1]

    def clear_loop(self, storage_key):
        self._r.delete(self._lkey(storage_key))

    def reset(self):
        for key in self._r.scan_iter(f"{self._p}*"):
            self._r.delete(key)


def build_state_store() -> StateStore:
    """In-memory by default; Redis when ``REDIS_URL`` is set and reachable."""
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return InMemoryStateStore()
    try:
        import redis

        client = redis.from_url(url, decode_responses=True)
        client.ping()
        logger.info("Gateway state backend: Redis (%s)", url)
        return RedisStateStore(client)
    except Exception as exc:  # noqa: BLE001 — any Redis failure degrades to memory
        logger.warning("Gateway state backend: Redis unavailable (%s); using in-memory store", exc)
        return InMemoryStateStore()
