from .db import NodeDatabase

class NodeConfig:
    def __init__(self, node_id, port, dlm_url, other_nodes):
        self.node_id = node_id
        self.port = port
        self.dlm_url = dlm_url
        self.other_nodes = other_nodes

        # Her node kendi DB'sini burada oluşturur
        self.db = NodeDatabase(node_id)
