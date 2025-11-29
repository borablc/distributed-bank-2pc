from dataclasses import dataclass
from .db import NodeDatabase


@dataclass
class NodeConfig:
    node_id: int
    port: int
    dlm_url: str
    other_nodes: list
    db: NodeDatabase


# Uygulama içinde her yerden erişebilmek için basit bir global
_current_config: NodeConfig | None = None


def init_config(node_id: int, port: int, dlm_url: str, other_nodes: list[str]):
    global _current_config
    db = NodeDatabase(node_id)
    _current_config = NodeConfig(
        node_id=node_id,
        port=port,
        dlm_url=dlm_url,
        other_nodes=other_nodes,
        db=db,
    )
    return _current_config


def get_config() -> NodeConfig:
    if _current_config is None:
        raise RuntimeError("NodeConfig is not initialized")
    return _current_config
