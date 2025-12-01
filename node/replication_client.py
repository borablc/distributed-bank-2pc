# node/replication_client.py
import requests
from .config import get_config


class ReplicationError(Exception):
    pass


def _post_json(base_url: str, path: str, payload: dict, timeout: float = 2.0):
    url = base_url.rstrip("/") + path
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.RequestException as e:
        raise ReplicationError(f"Request to {url} failed: {e}")
    return resp


def prepare_all(account_id: int, new_balance: int, tx_id: str) -> bool:
    cfg = get_config()
    payload = {
        "tx_id": tx_id,
        "account_id": account_id,
        "new_balance": new_balance,
    }

    for base in cfg.other_nodes:
        resp = _post_json(base, "/prepare", payload)
        if resp.status_code != 200:
            return False
        data = resp.json()
        if data.get("vote") != "YES":
            return False
    return True


def commit_all(tx_id: str):
    cfg = get_config()
    payload = {"tx_id": tx_id}

    for base in cfg.other_nodes:
        resp = _post_json(base, "/commit", payload)
        if resp.status_code != 200:
            raise ReplicationError(f"Commit failed on {base}: {resp.text}")


def abort_all(tx_id: str):
    cfg = get_config()
    payload = {"tx_id": tx_id}

    for base in cfg.other_nodes:
        try:
            _post_json(base, "/abort", payload)
        except ReplicationError:
            # Logging can be made here.
            pass
