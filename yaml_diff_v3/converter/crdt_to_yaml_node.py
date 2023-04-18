from collections import OrderedDict

from yaml_diff_v3 import crdt_graph, yaml_graph, utils


def _scalar_to_yaml(node: crdt_graph.ScalarNode) -> yaml_graph.ScalarNode:
    return yaml_graph.ScalarNode(
        path=node.yaml_path,  # TODO: Is it really necessary?
        tag=node.yaml_tag,
        value=node.value,
    )


def _mapping_item_to_yaml(
        mapping_node: crdt_graph.MappingNode,
        item: crdt_graph.MappingNode.Item) -> tuple[yaml_graph.NodePathKey, yaml_graph.MappingNode.Item]:
    has_same_key = 1 < sum(1 for mapping_item in mapping_node.items if mapping_item.key.value == item.key.value)
    path_key = (item.key.value, item.value.id) if has_same_key else item.key.value

    yaml_key: yaml_graph.Node
    if not has_same_key:
        yaml_key = yaml_graph.ScalarNode(path=(), tag=item.key.yaml_tag, value=item.key.value)
    else:
        yaml_key = yaml_graph.SequenceNode(
            path=(),  # Note: path is not set because I was too lazy, and it is not used anyway
            tag=utils.get_tag("seq"),
            values=(
                yaml_graph.ScalarNode(path=(), tag=item.key.yaml_tag, value=item.key.value),
                yaml_graph.ScalarNode(path=(), tag=utils.get_tag("str"), value=item.value.id),
            )
        )

    yaml_item = yaml_graph.MappingNode.Item(
        key=yaml_key,
        value=_crdt_to_yaml_node(item.value),
        path_key=path_key,  # TODO: probably unnecessary
    )
    return path_key, yaml_item


def _mapping_to_yaml(node: crdt_graph.MappingNode) -> yaml_graph.MappingNode:
    items = OrderedDict(_mapping_item_to_yaml(node, item) for item in node.items if not item.value.is_hidden)
    return yaml_graph.MappingNode(
        path=node.yaml_path,
        tag=node.yaml_tag,
        items=items,
    )


def _crdt_to_yaml_node(crdt_node: crdt_graph.Node) -> yaml_graph.Node:
    if isinstance(crdt_node, crdt_graph.ScalarNode):
        return _scalar_to_yaml(crdt_node)
    if isinstance(crdt_node, crdt_graph.MappingNode):
        return _mapping_to_yaml(crdt_node)
    raise TypeError(f"Unexpected crdt node type {crdt_node}")


def crdt_graph_to_yaml_node(graph: crdt_graph.Graph) -> yaml_graph.Node:
    return _crdt_to_yaml_node(graph.root)
