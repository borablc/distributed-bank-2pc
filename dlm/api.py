from flask import Flask, request, jsonify
import redis
import json

app = Flask(__name__)

# Redis bağlantısı
r = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "message": "DLM alive"})


@app.route("/begin_tx", methods=["POST"])
def begin_tx():
    data = request.get_json()
    # Şimdilik placeholder
    return jsonify({"error": "begin_tx_not_implemented"}), 501


@app.route("/lock_acquire", methods=["POST"])
def lock_acquire():
    data = request.get_json()
    return jsonify({"error": "lock_acquire_not_implemented"}), 501


@app.route("/lock_extend", methods=["POST"])
def lock_extend():
    data = request.get_json()
    return jsonify({"error": "lock_extend_not_implemented"}), 501


@app.route("/unlock_all", methods=["POST"])
def unlock_all():
    data = request.get_json()
    return jsonify({"error": "unlock_all_not_implemented"}), 501


@app.route("/end_tx", methods=["POST"])
def end_tx():
    data = request.get_json()
    return jsonify({"error": "end_tx_not_implemented"}), 501


if __name__ == "__main__":
    app.run(port=6000, debug=True)
