"""Tracks all user IDs that have interacted with the bot."""

from __future__ import annotations

import json
from pathlib import Path

_STATE_FILE = Path(__file__).parent / "users_state.json"


def _load() -> set[int]:
    if _STATE_FILE.exists():
        return set(json.loads(_STATE_FILE.read_text()))
    return set()


def _save(ids: set[int]) -> None:
    _STATE_FILE.write_text(json.dumps(sorted(ids)))


def register(user_id: int) -> None:
    ids = _load()
    if user_id not in ids:
        ids.add(user_id)
        _save(ids)


def all_users() -> set[int]:
    return _load()
