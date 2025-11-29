import requests
from dataclasses import dataclass
from .config import get_config
import time


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

def acquire_lock(tx_id: str, resource_id: int, mode: str,
                 max_retries: int = 3, retry_delay: float = 0.2):
    """
    mode: "S" veya "X"
    Dönüş:
      - lock alınırsa return
      - genç tx ise hemen DlmClientError (ABORT)
      - yaşlı tx ise birkaç kere RETRY dener, yine olmazsa error
    """
    cfg = get_config()
    url = cfg.dlm_url.rstrip("/") + "/lock_acquire"

    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json={
                "tx_id": tx_id,
                "resource_id": resource_id,
                "mode": mode,
            }, timeout=2)
        except requests.RequestException as e:
            raise DlmClientError(f"DLM lock_acquire failed: {e}")

        if resp.status_code != 200:
            raise DlmClientError(f"DLM lock_acquire error: {resp.status_code} {resp.text}")

        data = resp.json()
        status = data.get("status")
        reason = data.get("reason")

        if status == "GRANTED":
            return  # başarı

        if status == "ABORT":
            raise DlmClientError(f"Lock aborted by DLM (Wait-Die): {reason}")

        if status == "RETRY":
            # Yaşlı tx -> bekle, tekrar dene
            time.sleep(retry_delay)
            continue

        raise DlmClientError(f"Unknown lock status from DLM: {status}")

    # max_retries bitti
    raise DlmClientError("Lock acquire RETRY limit exceeded")


def extend_lock(tx_id: str, resource_id: int) -> bool:
    cfg = get_config()
    url = cfg.dlm_url.rstrip("/") + "/lock_extend"

    try:
        resp = requests.post(url, json={
            "tx_id": tx_id,
            "resource_id": resource_id,
        }, timeout=2)
    except requests.RequestException as e:
        raise DlmClientError(f"DLM lock_extend failed: {e}")

    if resp.status_code != 200:
        raise DlmClientError(f"DLM lock_extend error: {resp.status_code} {resp.text}")

    data = resp.json()
    return bool(data.get("ok"))


def unlock_all(tx_id: str):
    cfg = get_config()
    url = cfg.dlm_url.rstrip("/") + "/unlock_all"

    try:
        resp = requests.post(url, json={"tx_id": tx_id}, timeout=2)
    except requests.RequestException as e:
        raise DlmClientError(f"DLM unlock_all failed: {e}")

    if resp.status_code != 200:
        raise DlmClientError(f"DLM unlock_all error: {resp.status_code} {resp.text}")
