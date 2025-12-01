from flask import Flask, request, jsonify
from .config import get_config
from . import node_service

app = Flask(__name__)


@app.route("/ping")
def ping():
    cfg = get_config()
    return jsonify({"node_id": cfg.node_id, "status": "ok"})


@app.route("/balance/<int:account_id>", methods=["GET"])
def get_balance(account_id):
    try:
        account_id = int(account_id)
    except ValueError:
        return jsonify({"error": "account_id_must_be_int"}), 400

    body, code = node_service.get_balance(account_id)
    return jsonify(body), code


@app.route("/deposit", methods=["POST"])
def deposit():
    data = request.get_json(force=True) or {}
    account_id = data.get("account_id")
    amount = data.get("amount")

    if account_id is None or amount is None:
        return jsonify({"error": "account_id_and_amount_required"}), 400

    try:
        account_id = int(account_id)
        amount = int(amount)
    except ValueError:
        return jsonify({"error": "account_id_and_amount_must_be_int"}), 400

    if amount <= 0:
        return jsonify({"error": "amount_must_be_positive"}), 400

    body, code = node_service.deposit(account_id, amount)
    return jsonify(body), code


@app.route("/transfer", methods=["POST"])
def transfer():
    data = request.get_json(force=True) or {}
    from_id = data.get("from_id")
    to_id = data.get("to_id")
    amount = data.get("amount")

    if from_id is None or to_id is None or amount is None:
        return jsonify({"error": "from_id_and_to_id_and_amount_required"}), 400

    try:
        from_id = int(from_id)
        to_id = int(to_id)
        amount = int(amount)
    except ValueError:
        return jsonify({"error": "from_id_and_to_id_and_amount_must_be_int"}), 400

    if amount <= 0:
        return jsonify({"error": "amount_must_be_positive"}), 400

    if from_id == to_id:
        return jsonify({"error": "from_and_to_cannot_be_same_account"}), 400

    body, code = node_service.transfer(from_id, to_id, amount)
    return jsonify(body), code


@app.route("/test_s_lock/<int:account_id>", methods=["GET"])
def test_s_lock(account_id):
    try:
        account_id = int(account_id)
    except ValueError:
        return jsonify({"error": "account_id_must_be_int"}), 400

    body, code = node_service.test_s_lock(account_id)
    return jsonify(body), code


@app.route("/test_x_lock/<int:account_id>", methods=["GET"])
def test_x_lock(account_id):
    try:
        account_id = int(account_id)
    except ValueError:
        return jsonify({"error": "account_id_must_be_int"}), 400

    body, code = node_service.test_x_lock(account_id)
    return jsonify(body), code


@app.route("/prepare", methods=["POST"])
def prepare():
    data = request.get_json(force=True) or {}
    tx_id = data.get("tx_id")
    account_id = data.get("account_id")
    new_balance = data.get("new_balance")

    if tx_id is None or account_id is None or new_balance is None:
        return jsonify({"vote": "NO", "error": "tx_id_account_id_new_balance_required"}), 400

    try:
        account_id = int(account_id)
        new_balance = int(new_balance)
    except ValueError:
        return jsonify({"vote": "NO", "error": "account_id_and_new_balance_must_be_int"}), 400

    body, code = node_service.prepare(tx_id, account_id, new_balance)
    return jsonify(body), code


@app.route("/commit", methods=["POST"])
def commit():
    data = request.get_json(force=True) or {}
    tx_id = data.get("tx_id")

    if tx_id is None:
        return jsonify({"error": "tx_id_required"}), 400

    body, code = node_service.commit_tx(tx_id)
    return jsonify(body), code


@app.route("/abort", methods=["POST"])
def abort():
    data = request.get_json(force=True) or {}
    tx_id = data.get("tx_id")

    if tx_id is None:
        return jsonify({"error": "tx_id_required"}), 400

    body, code = node_service.abort_tx(tx_id)
    return jsonify(body), code
