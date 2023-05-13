from typing import Generator

from yaml_diff_v3 import yaml_graph
from yaml_diff_v3.crdt_graph.nodes import Node, NodeId, MappingNode


class Graph:
    def __init__(self, root: Node):
        self.root = root

    def get_path_to_node_mapping(self) -> dict[yaml_graph.NodePath, Node | MappingNode.Item]:
        # TODO: eval yaml_path in runtime
        return {node.yaml_path: node for node in self._iter_nodes()}

    def get_node(self, node_id: NodeId) -> Node | MappingNode.Item:
        [node] = [node for node in self._iter_nodes() if node.id == node_id]
        return node

    def _iter_nodes(self) -> Generator[Node | MappingNode.Item, None, None]:
        def dfs(node: Node) -> Generator[Node | MappingNode.Item, None, None]:
            yield node
            for child in node.get_children():
                yield from dfs(child)

        yield from dfs(self.root)
