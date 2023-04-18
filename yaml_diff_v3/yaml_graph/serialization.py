from collections import OrderedDict

from ruamel import yaml
from ruamel.yaml.error import FileMark

from yaml_diff_v3.yaml_graph import nodes
from yaml_diff_v3.yaml_graph.nodes import NodePath, NodePathKey


def _make_dummy_mark() -> FileMark:
    return FileMark("<file>", 0, 0, 0)


def _get_default_yaml_kwargs():
    return dict(
        start_mark=_make_dummy_mark(),  # Can't be None
        end_mark=_make_dummy_mark(),
        comment=None,
        anchor=None,
    )


def _yaml_node_as_path_key(serialized: yaml.Node) -> NodePathKey:
    if isinstance(serialized, yaml.ScalarNode):
        return serialized.value
    if isinstance(serialized, yaml.SequenceNode) and len(serialized.value) == 2 and \
            all(isinstance(item, yaml.ScalarNode) for item in serialized.value):
        return tuple(item.value for item in serialized.value)
    raise TypeError("Only a scalar or a pair of scalars can be a key")


def _deserialize_scalar(serialized: yaml.ScalarNode, path: NodePath) -> nodes.ScalarNode:
    return nodes.ScalarNode(
        path=path,
        tag=serialized.tag,
        value=serialized.value,
    )


def _serialize_scalar(node: nodes.ScalarNode) -> yaml.ScalarNode:
    return yaml.ScalarNode(
        tag=node.tag,
        value=node.value,
        style=None,  # TODO: fill
        **_get_default_yaml_kwargs(),
    )


def _deserialize_mapping(serialized: yaml.MappingNode, path: NodePath) -> nodes.MappingNode:
    assert serialized.merge is None, serialized  # TODO: find out when it is not None

    items = OrderedDict()  # type: OrderedDict[str, nodes.MappingNode.Item]
    for key, value in serialized.value:
        path_key: NodePathKey = _yaml_node_as_path_key(key)
        item_path = path + (path_key,)
        key_node = _deserialize_node(key, item_path + (0,))
        value_node = _deserialize_node(value, item_path + (1,))
        items[path_key] = nodes.MappingNode.Item(key=key_node, value=value_node, path_key=path_key)

    return nodes.MappingNode(path=path, tag=serialized.tag, items=items)


def _serialize_mapping(node: nodes.MappingNode) -> yaml.MappingNode:
    serialized = yaml.MappingNode(
        tag=node.tag,
        value=[(_serialize_node(item.key), _serialize_node(item.value)) for item in node.items.values()],
        flow_style=None,  # TODO: fill
        **_get_default_yaml_kwargs(),
    )
    serialized.merge = None  # TODO: find out when it is not None
    return serialized


def _deserialize_sequence(serialized: yaml.SequenceNode, path: NodePath) -> nodes.SequenceNode:
    return nodes.SequenceNode(
        path=path,
        tag=serialized.tag,
        values=tuple(_deserialize_node(value, path + (i,)) for i, value in enumerate(serialized.value)),
    )


def _serialize_sequence(node: nodes.SequenceNode) -> yaml.SequenceNode:
    return yaml.SequenceNode(
        tag=node.tag,
        value=[_serialize_node(value) for value in node.values],
        flow_style=None,  # TODO: fill
        **_get_default_yaml_kwargs(),
    )


def _deserialize_node(serialized: yaml.Node, path: NodePath) -> nodes.Node:
    if isinstance(serialized, yaml.ScalarNode):
        return _deserialize_scalar(serialized, path)
    if isinstance(serialized, yaml.MappingNode):
        return _deserialize_mapping(serialized, path)
    if isinstance(serialized, yaml.SequenceNode):
        return _deserialize_sequence(serialized, path)
    raise Exception(f"Unexpected yaml node {serialized}")


def _serialize_node(node: nodes.Node) -> yaml.Node:
    if isinstance(node, nodes.ScalarNode):
        return _serialize_scalar(node)
    if isinstance(node, nodes.MappingNode):
        return _serialize_mapping(node)
    if isinstance(node, nodes.SequenceNode):
        return _serialize_sequence(node)
    raise Exception(f"Unexpected graph node {node}")


def deserialize(serialized: yaml.Node) -> nodes.Node:
    return _deserialize_node(serialized, path=())


def serialize(node: nodes.Node) -> yaml.Node:
    return _serialize_node(node)
