# dlm/tx_manager.py
from dataclasses import dataclass
from .storage import get_redis

TX_COUNTER_KEY = "tx:global_ts"


@dataclass
class TxInfo:
    tx_id: str
    ts: int
    node_id: int
    status: str


def begin_tx(node_id: int) -> TxInfo:
    r = get_redis()

    ts = r.incr(TX_COUNTER_KEY)

    tx_id = f"{node_id}-{ts}"

    key = f"tx:{tx_id}"
    r.hset(key, mapping={
        "tx_id": tx_id,
        "ts": ts,
        "node_id": node_id,
        "status": "ACTIVE",
    })

    return TxInfo(tx_id=tx_id, ts=ts, node_id=node_id, status="ACTIVE")


def end_tx(tx_id: str):
    r = get_redis()
    key = f"tx:{tx_id}"

    if not r.exists(key):
        return

    r.hset(key, "status", "FINISHED")


def get_tx_ts(tx_id: str) -> int | None:
    """
    Wait-Die için transaction'ın timestamp'ini döner.
    tx_id yoksa None döner.
    """
    r = get_redis()
    key = f"tx:{tx_id}"
    data = r.hgetall(key)
    if not data:
        return None
    return int(data["ts"])

