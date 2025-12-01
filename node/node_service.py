import time
from .config import get_config
from . import dlm_client, replication_client

def get_balance(account_id: int):
    cfg = get_config()
    tx = None

    try:
        tx = dlm_client.begin_tx()
        dlm_client.acquire_lock(tx.tx_id, account_id, "S")

        balance = cfg.db.get_balance(account_id)
        if balance is None:
            return {"error": "account_not_found"}, 404

        return {
            "node_id": cfg.node_id,
            "account_id": account_id,
            "balance": balance,
            "tx_id": tx.tx_id,
        }, 200

    except dlm_client.DlmClientError as e:
        return {"error": "dlm_error", "detail": str(e)}, 500

    finally:
        if tx is not None:
            try:
                dlm_client.unlock_all(tx.tx_id)
            except:
                # logging can be made here
                pass
            try:
                dlm_client.end_tx(tx.tx_id)
            except:
                # logging can be made here
                pass

def deposit(account_id: int, amount: int):
    cfg = get_config()
    tx = None
    has_txn_begin = False

    try:
        tx = dlm_client.begin_tx()
        dlm_client.acquire_lock(tx.tx_id, account_id, "X")

        old_balance = cfg.db.get_balance(account_id)
        if old_balance is None:
            return {"error": "account_not_found"}, 404

        new_balance = old_balance + amount

        ok = replication_client.prepare_all(account_id, new_balance, tx.tx_id)
        if not ok:
            replication_client.abort_all(tx.tx_id)
            return {"error": "prepare_phase_failed"}, 500

        cfg.db.begin()
        has_txn_begin = True
        cfg.db.update_balance(account_id, new_balance)
        cfg.db.commit()
        has_txn_begin = False

        replication_client.commit_all(tx.tx_id)

        return {
            "status": "ok",
            "node_id": cfg.node_id,
            "account_id": account_id,
            "old_balance": old_balance,
            "new_balance": new_balance,
            "tx_id": tx.tx_id,
        }, 200

    except dlm_client.DlmClientError as e:
        if has_txn_begin:
            cfg.db.rollback()
        if tx is not None:
            replication_client.abort_all(tx.tx_id)
        return {"error": "dlm_error", "detail": str(e)}, 500

    except replication_client.ReplicationError as e:
        if has_txn_begin:
            cfg.db.rollback()
        if tx is not None:
            replication_client.abort_all(tx.tx_id)
        return {"error": "replication_error", "detail": str(e)}, 500

    finally:
        if tx is not None:
            try:
                dlm_client.unlock_all(tx.tx_id)
            except:
                # logging can be made here
                pass
            try:
                dlm_client.end_tx(tx.tx_id)
            except:
                # logging can be made here
                pass

def transfer(from_id: int, to_id: int, amount: int):
    cfg = get_config()
    tx = None
    has_txn_begin = False

    first = min(from_id, to_id)
    second = max(from_id, to_id)
    try:
        tx = dlm_client.begin_tx()

        dlm_client.acquire_lock(tx.tx_id, first, "X")
        dlm_client.acquire_lock(tx.tx_id, second, "X")

        from_old_balance = cfg.db.get_balance(from_id)
        if from_old_balance is None:
            return {"error": "from_account_not_found"}, 404
        if from_old_balance < amount:
            return {"error": "balance_not_enough"}, 400

        to_old_balance = cfg.db.get_balance(to_id)
        if to_old_balance is None:
            return {"error": "to_account_not_found"}, 404

        from_new_balance = from_old_balance - amount
        to_new_balance = to_old_balance + amount

        from_ok = replication_client.prepare_all(from_id, from_new_balance, tx.tx_id)
        if not from_ok:
            replication_client.abort_all(tx.tx_id)
            return {"error": "prepare_phase_failed"}, 500

        to_ok = replication_client.prepare_all(to_id, to_new_balance, tx.tx_id)
        if not to_ok:
            replication_client.abort_all(tx.tx_id)
            return {"error": "prepare_phase_failed"}, 500

        cfg.db.begin()
        has_txn_begin = True
        cfg.db.update_balance(from_id, from_new_balance)
        cfg.db.update_balance(to_id, to_new_balance)
        cfg.db.commit()
        has_txn_begin = False

        replication_client.commit_all(tx.tx_id)

        return {
            "status": "ok",
            "node_id": cfg.node_id,
            "from_id": from_id,
            "from_old_balance": from_old_balance,
            "from_new_balance": from_new_balance,
            "to_id": to_id,
            "to_old_balance": to_old_balance,
            "to_new_balance": to_new_balance,
            "amount": amount,
            "tx_id": tx.tx_id,
        },200

    except dlm_client.DlmClientError as e:
        if has_txn_begin:
            cfg.db.rollback()
        if tx is not None:
            replication_client.abort_all(tx.tx_id)
        return {"error": "dlm_error", "detail": str(e)}, 500

    except replication_client.ReplicationError as e:
        if has_txn_begin:
            cfg.db.rollback()
        if tx is not None:
            replication_client.abort_all(tx.tx_id)
        return {"error": "replication_error", "detail": str(e)}, 500

    finally:
        if tx is not None:
            try:
                dlm_client.unlock_all(tx.tx_id)
            except:
                # logging can be made here
                pass
            try:
                dlm_client.end_tx(tx.tx_id)
            except:
                # logging can be made here
                pass

def test_s_lock(account_id:int):
    tx = None
    cfg = get_config()

    try:
        tx = dlm_client.begin_tx()
        dlm_client.acquire_lock(tx.tx_id, account_id, "S")
        time.sleep(3)

        return {
            "status": "ok",
            "node": cfg.node_id,
            "account_id": account_id,
            "lock_mode": "s_lock",
            "tx_id": tx.tx_id,
        }, 200

    except dlm_client.DlmClientError as e:
        return {"error": "dlm_error", "detail": str(e)}, 500

    finally:
        if tx is not None:
            try:
                dlm_client.unlock_all(tx.tx_id)
            except:
                pass
            try:
                dlm_client.end_tx(tx.tx_id)
            except:
                pass

def test_x_lock(account_id:int):
    tx = None
    cfg = get_config()

    try:
        tx = dlm_client.begin_tx()
        dlm_client.acquire_lock(tx.tx_id, account_id, "X")
        time.sleep(3)

        return {
            "status": "ok",
            "node": cfg.node_id,
            "account_id": account_id,
            "lock_mode": "x_lock",
            "tx_id": tx.tx_id,
        }, 200
    except dlm_client.DlmClientError as e:
        return {"error": "dlm_error", "detail": str(e)}, 500

    finally:
        if tx is not None:
            try:
                dlm_client.unlock_all(tx.tx_id)
            except:
                pass
            try:
                dlm_client.end_tx(tx.tx_id)
            except:
                pass

# 2PC PARTICIPANT (prepare / commit / abort)
def prepare(tx_id: str, account_id: int, new_balance: int):
    cfg = get_config()

    try:
        dlm_client.acquire_lock(tx_id, account_id, "X")
    except dlm_client.DlmClientError as e:
        return {"vote": "NO", "error": str(e)}, 200

    balance = cfg.db.get_balance(account_id)
    if balance is None:
        return {"vote": "NO", "error": "account_not_found"}, 200

    cfg.prepared_txs.setdefault(tx_id, []).append({"account_id": account_id, "new_balance": new_balance})

    return {"vote": "YES"}, 200

def commit_tx(tx_id: str):
    cfg = get_config()
    updates = cfg.prepared_txs.pop(tx_id, None)

    if updates is None:
        return {"ok": True, "info": "nothing_to_commit"}, 200

    try:
        cfg.db.begin()
        for upd in updates:
            acc_id = upd["account_id"]
            new_balance = upd["new_balance"]
            cfg.db.update_balance(acc_id, new_balance)
        cfg.db.commit()
    except:
        cfg.db.rollback()
        return {"ok": False, "info": "db_error_on_commit"}, 500

    return {"ok": True}, 200

def abort_tx(tx_id: str):
    cfg = get_config()
    cfg.prepared_txs.pop(tx_id, None)
    return {"ok": True}, 200
