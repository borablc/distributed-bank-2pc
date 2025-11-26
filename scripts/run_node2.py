import os
import sys

CURRENT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CURRENT)
sys.path.insert(0, ROOT)

from node.api import app
from node.config import NodeConfig

if __name__ == "__main__":
    app.config["NODE_CONFIG"] = NodeConfig(
        node_id=2,
        port=5002,
        dlm_url="http://127.0.0.1:5000",
        other_nodes=["http://127.0.0.1:5001"]
    )
    app.run(port=5002, debug=True)
