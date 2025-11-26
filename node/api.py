from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "message": "Node alive"})

# Business endpoints (şimdilik boş)
@app.route("/balance/<int:account_id>", methods=["GET"])
def get_balance(account_id):
    return jsonify({"error": "not_implemented"}), 501

@app.route("/deposit", methods=["POST"])
def deposit():
    return jsonify({"error": "not_implemented"}), 501

@app.route("/withdraw", methods=["POST"])
def withdraw():
    return jsonify({"error": "not_implemented"}), 501

@app.route("/transfer", methods=["POST"])
def transfer():
    return jsonify({"error": "not_implemented"}), 501

# 2PC participant endpoints
@app.route("/prepare", methods=["POST"])
def prepare():
    return jsonify({"error": "not_implemented"}), 501

@app.route("/commit", methods=["POST"])
def commit():
    return jsonify({"error": "not_implemented"}), 501

@app.route("/abort", methods=["POST"])
def abort():
    return jsonify({"error": "not_implemented"}), 501


if __name__ == "__main__":
    app.run(port=5001, debug=True)
