import typing

import yaml_diff_v3.crdt_graph.nodes as crdt
import yaml_diff_v3.yaml_graph.nodes as yaml
from yaml_diff_v3.utils import make_unique_id


def _make_new_node_kwargs(node_id: str, yaml_tag: str, anchor: None | str,
                          yaml_path: yaml.NodePath, ts: crdt.Timestamp) -> dict[str, typing.Any]:
    # See crdt.Node constructor
    return dict(
        id=crdt.NodeId(node_id),
        yaml_tag=yaml_tag,
        anchor=anchor,
        yaml_path=yaml_path,
        last_edit_ts=ts,
        is_deprecated=False,
        # is_all_parents_hidden=False,
    )


def _make_crdt_scalar_node(yaml_node: yaml.ScalarNode, node_id: str, ts: crdt.Timestamp) -> crdt.ScalarNode:
    return crdt.ScalarNode(
        value=yaml_node.value,
        **_make_new_node_kwargs(node_id, yaml_node.tag, yaml_node.anchor, yaml_node.path, ts),
    )


def _make_crdt_mapping_node(node_id: str, yaml_node: yaml.MappingNode, ts: crdt.Timestamp,
                            created_nodes: dict[yaml.NodePath, crdt.Node]) -> crdt.MappingNode:
    return crdt.MappingNode(
        items=[make_new_crdt_mapping_item_from_yaml(yaml_item, ts, created_nodes)
               for yaml_item in yaml_node.items.values()],
        **_make_new_node_kwargs(node_id, yaml_node.tag, yaml_node.anchor, yaml_node.path, ts),
    )


def _make_crdt_node(node_id: str, yaml_node: yaml.Node, ts: crdt.Timestamp,
                    created_nodes: dict[yaml.NodePath, crdt.Node]) -> crdt.Node:
    if isinstance(yaml_node, yaml.ReferenceNode):
        return crdt.ReferenceNode(crdt.NodeId(node_id), created_nodes[yaml_node.referred_node.path].id,
                                  is_deprecated=False, yaml_path=yaml_node.path)

    node: crdt.Node
    if isinstance(yaml_node, yaml.ScalarNode):
        node = _make_crdt_scalar_node(yaml_node, node_id, ts)
    elif isinstance(yaml_node, yaml.MappingNode):
        node = _make_crdt_mapping_node(node_id, yaml_node, ts, created_nodes)
    # elif isinstance(yaml_node, yaml.SequenceNode):
    #     pass
    else:
        raise NotImplementedError(f"Unexpected yaml node {yaml_node}")

    created_nodes[yaml_node.path] = node
    return node


def make_new_crdt_mapping_item_from_yaml(yaml_item: yaml.MappingNode.Item, ts: crdt.Timestamp,
                                         path_to_node_mapping: dict[yaml.NodePath, crdt.Node]) -> crdt.MappingNode.Item:
    if not isinstance(yaml_item.key, yaml.ScalarNode):
        raise TypeError(f"Locally added key can't be composite")
    return crdt.MappingNode.Item(
        key=_make_crdt_scalar_node(yaml_item.key, make_unique_id(), ts),
        value=_make_crdt_node(make_unique_id(), yaml_item.value, ts, created_nodes=path_to_node_mapping),
    )


def make_new_crdt_node_from_yaml(yaml_node: yaml.Node, ts: crdt.Timestamp) -> crdt.Node:
    node_id = make_unique_id()
    created_nodes: dict[yaml.NodePath, crdt.Node] = {}
    return _make_crdt_node(node_id, yaml_node, ts, created_nodes)
