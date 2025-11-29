from flask import Flask, request, jsonify
from .storage import get_redis
from .tx_manager import begin_tx as tm_begin_tx, end_tx as tm_end_tx
from .lock_manager import acquire_lock, extend_lock, unlock_all as lm_unlock_all
import json

app = Flask(__name__)

# Redis bağlantısı
r = get_redis()

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "message": "DLM alive"})


@app.route("/begin_tx", methods=["POST"])
def begin_tx():
    data = request.get_json(force=True) or {}
    node_id = data.get("node_id")
    if node_id is None:
        return jsonify({"error": "node_id_required"}), 400

    tx_info = tm_begin_tx(int(node_id))
    return jsonify({
        "tx_id": tx_info.tx_id,
        "ts": tx_info.ts,
        "node_id": tx_info.node_id,
        "status": tx_info.status,
    })



@app.route("/lock_acquire", methods=["POST"])
def lock_acquire():
    data = request.get_json(force=True) or {}
    tx_id = data.get("tx_id")
    resource_id = data.get("resource_id")
    mode = data.get("mode")  # "S" veya "X"

    if not tx_id or resource_id is None or mode not in ("S", "X"):
        return jsonify({"error": "tx_id_resource_id_mode_required"}), 400

    try:
        resource_id = int(resource_id)
    except ValueError:
        return jsonify({"error": "resource_id_must_be_int"}), 400

    result = acquire_lock(tx_id=tx_id, resource_id=resource_id, mode=mode)  # type: ignore

    print(f"Lock result: {result.status} Lock reason: {result.reason}, tx_id: {tx_id}, resource_id: {resource_id}, mode: {mode}")

    return jsonify({
        "status": result.status,
        "reason": result.reason,
    })


@app.route("/lock_extend", methods=["POST"])
def lock_extend():
    data = request.get_json(force=True) or {}
    tx_id = data.get("tx_id")
    resource_id = data.get("resource_id")

    if not tx_id or resource_id is None:
        return jsonify({"error": "tx_id_resource_id_required"}), 400

    try:
        resource_id = int(resource_id)
    except ValueError:
        return jsonify({"error": "resource_id_must_be_int"}), 400

    ok = extend_lock(tx_id=tx_id, resource_id=resource_id)
    return jsonify({"ok": ok})


@app.route("/unlock_all", methods=["POST"])
def unlock_all():
    data = request.get_json(force=True) or {}
    tx_id = data.get("tx_id")

    if not tx_id:
        return jsonify({"error": "tx_id_required"}), 400

    lm_unlock_all(tx_id)
    return jsonify({"ok": True})



@app.route("/end_tx", methods=["POST"])
def end_tx():
    data = request.get_json(force=True) or {}
    tx_id = data.get("tx_id")
    if not tx_id:
        return jsonify({"error": "tx_id_required"}), 400

    tm_end_tx(tx_id)
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
