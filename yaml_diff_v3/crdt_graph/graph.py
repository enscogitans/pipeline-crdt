from yaml_diff_v3 import yaml_graph
from yaml_diff_v3.crdt_graph.nodes import Node, NodeId, MappingNode, SequenceNode


class Graph:
    def __init__(self, root: Node):
        self.root = root

    def get_path_to_node_mapping(self) -> dict[yaml_graph.NodePath, Node | MappingNode.Item]:
        def dfs(node: Node, path):
            if not isinstance(node, (MappingNode.Item, SequenceNode.Item)):  # they do not store it
                node.yaml_path = path
            yield path, node
            for path_key, child in node.get_children_with_path():
                yield from dfs(child, path + (path_key,))

        return {path: node for path, node in dfs(self.root, ())}

    def get_node(self, node_id: NodeId) -> Node | MappingNode.Item:
        def dfs(node: Node):
            yield node
            for child in node.get_all_children():
                yield from dfs(child)

        [node] = [node for node in dfs(self.root) if node.id == node_id]
        return node

    # def get_parent(self, node_id: NodeId) -> Node | MappingNode.Item | SequenceNode.Item:
    #     def dfs(node: Node, parent):
    #         yield node, parent
    #         for child in node.get_all_children():
    #             yield from dfs(child, node)
    #
    #     [(node, parent)] = [(node, parent) for node, parent in dfs(self.root, None) if node.id == node_id]
    #     return node
