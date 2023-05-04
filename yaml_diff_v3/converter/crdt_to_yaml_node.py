from collections import OrderedDict

from yaml_diff_v3 import crdt_graph, yaml_graph, utils


def _scalar_to_yaml(node: crdt_graph.ScalarNode) -> yaml_graph.ScalarNode:
    return yaml_graph.ScalarNode(
        path=(),  # TODO: remove path
        tag=node.yaml_tag,
        value=node.value,
        anchor=node.anchor,
    )


def _mapping_item_to_yaml(
        mapping_node: crdt_graph.MappingNode,
        item: crdt_graph.MappingNode.Item,
        converted_nodes: dict[crdt_graph.NodeId, yaml_graph.Node],
) -> tuple[yaml_graph.NodePathKey, yaml_graph.MappingNode.Item]:
    has_same_key = 1 < sum(1 for mapping_item in mapping_node.items if mapping_item.key.value == item.key.value)
    path_key = (item.key.value, item.value.id) if has_same_key else item.key.value

    assert item.key.anchor is None, "Key can't cave an anchor"
    yaml_key: yaml_graph.Node
    if not has_same_key:
        yaml_key = yaml_graph.ScalarNode(path=(), tag=item.key.yaml_tag, value=item.key.value, anchor=None)
    else:
        yaml_key = yaml_graph.SequenceNode(
            path=(),  # Note: path is not set because I was too lazy, and it is not used anyway
            tag=utils.get_tag("seq"),
            values=(
                yaml_graph.ScalarNode(path=(), tag=item.key.yaml_tag, value=item.key.value, anchor=None),
                yaml_graph.ScalarNode(path=(), tag=utils.get_tag("str"), value=item.value.id, anchor=None),
            ),
            anchor=None,
        )

    yaml_item = yaml_graph.MappingNode.Item(
        key=yaml_key,
        value=_crdt_to_yaml_node(item.value, converted_nodes),
        path_key=path_key,  # TODO: probably unnecessary
    )
    return path_key, yaml_item


def _mapping_to_yaml(node: crdt_graph.MappingNode,
                     converted_nodes: dict[crdt_graph.NodeId, yaml_graph.Node]) -> yaml_graph.MappingNode:
    items = OrderedDict(_mapping_item_to_yaml(node, item, converted_nodes)
                        for item in sorted(
                            node.items,
                            key=lambda item: (getattr(item.value, "anchor", "") is None, item.key.value))
                        if not item.value.is_hidden)
    return yaml_graph.MappingNode(
        path=node.yaml_path,
        tag=node.yaml_tag,
        items=items,
        anchor=node.anchor,
    )


def _crdt_to_yaml_node(crdt_node: crdt_graph.Node,
                       converted_nodes: dict[crdt_graph.NodeId, yaml_graph.Node]) -> yaml_graph.Node:
    if isinstance(crdt_node, crdt_graph.ReferenceNode):
        return yaml_graph.ReferenceNode(path=crdt_node.yaml_path,
                                        referred_node=converted_nodes[crdt_node.referred_id])

    converted: yaml_graph.Node
    if isinstance(crdt_node, crdt_graph.ScalarNode):
        converted = _scalar_to_yaml(crdt_node)
    elif isinstance(crdt_node, crdt_graph.MappingNode):
        converted = _mapping_to_yaml(crdt_node, converted_nodes)
    else:
        raise TypeError(f"Unexpected crdt node type {crdt_node}")

    converted_nodes[crdt_node.id] = converted
    return converted


def crdt_graph_to_yaml_node(graph: crdt_graph.Graph) -> yaml_graph.Node:
    converted_nodes: dict[crdt_graph.NodeId, yaml_graph.Node] = {}
    return _crdt_to_yaml_node(graph.root, converted_nodes)
