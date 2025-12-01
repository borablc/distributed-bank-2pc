# dlm/lock_manager.py
import json
import time
from dataclasses import dataclass
from typing import Literal
from .storage import get_redis
from .tx_manager import get_tx_ts

LockMode = Literal["S", "X"]
LOCK_TIMEOUT_SECONDS = 10.0


@dataclass
class LockResult:
    status: Literal["GRANTED", "RETRY", "ABORT"]
    reason: str | None = None


def _lock_key(resource_id: int) -> str:
    return f"lock:{resource_id}"


def _tx_locks_key(tx_id: str) -> str:
    return f"tx_locks:{tx_id}"


def _load_holders(resource_id: int):
    r = get_redis()
    raw = r.get(_lock_key(resource_id))
    if not raw:
        return []

    holders = json.loads(raw)

    # Cleaning the expired locks
    now = time.time()
    alive = [h for h in holders if h.get("expires_at", 0) > now]

    if len(alive) != len(holders):
        # If there is expired locks, update the redis
        if alive:
            r.set(_lock_key(resource_id), json.dumps(alive))
        else:
            r.delete(_lock_key(resource_id))

    return alive


def _save_holders(resource_id: int, holders):
    r = get_redis()
    if holders:
        r.set(_lock_key(resource_id), json.dumps(holders))
    else:
        r.delete(_lock_key(resource_id))


def _add_tx_lock_mapping(tx_id: str, resource_id: int):
    r = get_redis()
    key = _tx_locks_key(tx_id)
    raw = r.get(key)
    resources: list[int]
    if raw:
        resources = json.loads(raw)
    else:
        resources = []
    if resource_id not in resources:
        resources.append(resource_id)
        r.set(key, json.dumps(resources))


def _remove_tx_lock_mapping(tx_id: str):
    r = get_redis()
    r.delete(_tx_locks_key(tx_id))


def acquire_lock(tx_id: str, resource_id: int, mode: LockMode) -> LockResult:
    tx_ts = get_tx_ts(tx_id)
    if tx_ts is None:
        return LockResult(status="ABORT", reason="unknown_tx")

    holders = _load_holders(resource_id)

    # If same txn take the same lock before, return GRANTED
    existing = [h for h in holders if (h["tx_id"] == tx_id and h["mode"] == mode)]
    if existing:
        return LockResult(status="GRANTED", reason="lock_already_acquired")

    # If there is no holder, return GRANTED
    if not holders:
        expires_at = time.time() + LOCK_TIMEOUT_SECONDS
        holders.append({
            "tx_id": tx_id,
            "mode": mode,
            "ts": tx_ts,
            "expires_at": expires_at,
        })
        _save_holders(resource_id, holders)
        _add_tx_lock_mapping(tx_id, resource_id)
        return LockResult(status="GRANTED", reason="no_other_holders")

    #Check for conflicts, there can be multiple S-Locks on the same account.
    conflicting = []
    if mode == "S":
        for h in holders:
            if h["mode"] == "X" and h["tx_id"] != tx_id:
                conflicting.append(h)
    else:  # mode == "X"
        for h in holders:
            if h["tx_id"] != tx_id:
                conflicting.append(h)

    # If there is no conflict, return GRANTED
    if not conflicting:
        expires_at = time.time() + LOCK_TIMEOUT_SECONDS
        holders.append({
            "tx_id": tx_id,
            "mode": mode,
            "ts": tx_ts,
            "expires_at": expires_at,
        })
        _save_holders(resource_id, holders)
        _add_tx_lock_mapping(tx_id, resource_id)
        return LockResult(status="GRANTED", reason="no_conflicting_holders")

    # There is conflict so we need to check if its old or young.
    min_conflict_ts = min(int(h["ts"]) for h in conflicting)

    if tx_ts > min_conflict_ts:
        # Young -> DIE
        return LockResult(status="ABORT", reason="younger_than_conflict")
    else:
        # Old -> WAIT
        return LockResult(status="RETRY", reason="older_tx_should_wait")


def extend_lock(tx_id: str, resource_id: int) -> bool:
    holders = _load_holders(resource_id)
    changed = False
    now = time.time()
    new_exp = now + LOCK_TIMEOUT_SECONDS

    for h in holders:
        if h["tx_id"] == tx_id:
            h["expires_at"] = new_exp
            changed = True

    if changed:
        _save_holders(resource_id, holders)
        return True
    return False


def unlock_all(tx_id: str):
    r = get_redis()
    key = _tx_locks_key(tx_id)
    raw = r.get(key)

    if not raw:
        # logging can be done here
        return

    resources: list[int] = json.loads(raw)

    for resource_id in resources:
        holders = _load_holders(resource_id)
        new_holders = [h for h in holders if h["tx_id"] != tx_id]
        _save_holders(resource_id, new_holders)

    _remove_tx_lock_mapping(tx_id)
