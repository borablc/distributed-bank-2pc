import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from node.api import app
from node.config import init_config


if __name__ == "__main__":
    config = init_config(
        node_id=1,
        port=5001,
        dlm_url="http://127.0.0.1:5000",
        other_nodes=["http://127.0.0.1:5002"],
    )
    app.config["NODE_CONFIG"] = config

    app.run(port=config.port, debug=True)
