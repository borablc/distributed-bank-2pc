import os
import sys

CURRENT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CURRENT)
sys.path.insert(0, ROOT)

from node.api import app
from node.config import NodeConfig

if __name__ == "__main__":
    app.config["NODE_CONFIG"] = NodeConfig(
        node_id=1,
        port=5001,
        dlm_url="http://127.0.0.1:5000",
        other_nodes=["http://127.0.0.1:5002"]
    )
    app.run(port=5001, debug=True)
