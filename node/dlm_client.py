import requests
from dataclasses import dataclass
from .config import get_config


@dataclass
class TxHandle:
    tx_id: str
    ts: int


class DlmClientError(Exception):
    pass


def begin_tx() -> TxHandle:
    cfg = get_config()
    url = cfg.dlm_url.rstrip("/") + "/begin_tx"

    try:
        resp = requests.post(url, json={"node_id": cfg.node_id}, timeout=2)
    except requests.RequestException as e:
        raise DlmClientError(f"DLM begin_tx failed: {e}")

    if resp.status_code != 200:
        raise DlmClientError(f"DLM begin_tx error: {resp.status_code} {resp.text}")

    data = resp.json()
    return TxHandle(tx_id=data["tx_id"], ts=data["ts"])


def end_tx(tx_id: str):
    cfg = get_config()
    url = cfg.dlm_url.rstrip("/") + "/end_tx"

    try:
        resp = requests.post(url, json={"tx_id": tx_id}, timeout=2)
    except requests.RequestException as e:
        raise DlmClientError(f"DLM end_tx failed: {e}")

    if resp.status_code != 200:
        raise DlmClientError(f"DLM end_tx error: {resp.status_code} {resp.text}")
