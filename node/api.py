from flask import Flask, request, jsonify
from .config import get_config
from . import dlm_client


app = Flask(__name__)


@app.route("/ping", methods=["GET"])
def ping():
    cfg = get_config()
    return jsonify({
        "status": "ok",
        "message": f"Node {cfg.node_id} alive",
        "db_path": cfg.db.db_path,
    })


@app.route("/balance/<int:account_id>", methods=["GET"])
def get_balance(account_id):
    cfg = get_config()
    tx = None

    try:
        # 1) Transaction başlat
        tx = dlm_client.begin_tx()

        # 2) S-lock al (read lock)
        dlm_client.acquire_lock(tx.tx_id, account_id, mode="S")

        # 3) Local DB'den oku
        balance = cfg.db.get_balance(account_id)
        if balance is None:
            # Hesap yoksa 404 dönelim ama önce lockları bırakacağız
            resp = jsonify({"error": "account_not_found"})
            resp.status_code = 404
            return resp

        # 4) Başarılı durumda balance döndür
        return jsonify({
            "node_id": cfg.node_id,
            "account_id": account_id,
            "balance": balance,
            "tx_id": tx.tx_id,
        })

    except dlm_client.DlmClientError as e:
        # DLM ile ilgili bir hata
        return jsonify({"error": "dlm_error", "detail": str(e)}), 500

    finally:
        # 5) Ne olursa olsun lockları bırak ve tx'i bitir
        if tx is not None:
            try:
                dlm_client.unlock_all(tx.tx_id)
            except dlm_client.DlmClientError:
                # Burada çok zorlamaya gerek yok, loglarsın normalde
                pass
            try:
                dlm_client.end_tx(tx.tx_id)
            except dlm_client.DlmClientError:
                pass


@app.route("/deposit", methods=["POST"])
def deposit():
    return jsonify({"error": "not_implemented"}), 501


@app.route("/withdraw", methods=["POST"])
def withdraw():
    return jsonify({"error": "not_implemented"}), 501


@app.route("/transfer", methods=["POST"])
def transfer():
    return jsonify({"error": "not_implemented"}), 501


@app.route("/prepare", methods=["POST"])
def prepare():
    return jsonify({"error": "not_implemented"}), 501


@app.route("/commit", methods=["POST"])
def commit():
    return jsonify({"error": "not_implemented"}), 501


@app.route("/abort", methods=["POST"])
def abort():
    return jsonify({"error": "not_implemented"}), 501

@app.route("/debug_tx", methods=["POST"])
def debug_tx():
    try:
        tx = dlm_client.begin_tx()
        dlm_client.end_tx(tx.tx_id)
    except dlm_client.DlmClientError as e:
        return jsonify({"error": str(e)}), 500

    cfg = get_config()
    return jsonify({
        "node_id": cfg.node_id,
        "tx_id": tx.tx_id,
        "ts": tx.ts,
    })


if __name__ == "__main__":
    # Direkt çalıştırmak istersen (ama biz genelde scripts/run_nodeX.py kullanacağız)
    from .config import init_config
    cfg = init_config(
        node_id=1,
        port=5001,
        dlm_url="http://127.0.0.1:5000",
        other_nodes=[],
    )
    app.run(port=cfg.port, debug=True)
