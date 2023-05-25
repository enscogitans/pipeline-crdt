from collections import OrderedDict

from ruamel import yaml
from ruamel.yaml.error import FileMark

from yaml_diff_v3.yaml_graph import nodes
from yaml_diff_v3.yaml_graph.nodes import NodePath, NodePathKey


def _make_dummy_mark(column: int = 0) -> FileMark:
    return FileMark("<file>", 0, 0, column=column)


def _serialize_comment_token(token: nodes.Comment.Token) -> yaml.CommentToken:
    return yaml.CommentToken(
        value=token.value,
        # It is essential to set column to both these places. Otherwise, it won't work
        column=token.column,
        start_mark=_make_dummy_mark(column=token.column),
    )


def _deserialize_comment(yaml_comment: None | list[None | yaml.CommentToken]) -> None | nodes.Comment:
    if yaml_comment is None:
        return None
    tokens: list[None | nodes.Comment.Token | tuple[nodes.Comment.Token]] = []
    for token in yaml_comment:
        if token is None:
            tokens.append(None)
        elif isinstance(token, yaml.CommentToken):
            tokens.append(nodes.Comment.Token(token.value, token.column))
        else:
            assert isinstance(token, list)
            assert all(isinstance(inner, yaml.CommentToken) for inner in token)
            tokens.append(tuple(nodes.Comment.Token(inner.value, inner.column) for inner in token))
    return nodes.Comment(tuple(tokens))


def _serialize_comment(node_comment: None | nodes.Comment) -> None | \
                                                              list[None | yaml.CommentToken | list[yaml.CommentToken]]:
    if node_comment is None:
        return None
    result = []
    for value in node_comment.values:
        if value is None:
            result.append(None)
        elif isinstance(value, nodes.Comment.Token):
            result.append(_serialize_comment_token(value))
        else:
            assert isinstance(value, tuple)
            assert all(isinstance(inner, nodes.Comment.Token) for inner in value)
            result.append([_serialize_comment_token(inner) for inner in value])
    return result


def _get_default_yaml_kwargs():
    return dict(
        start_mark=_make_dummy_mark(),  # Can't be None
        end_mark=_make_dummy_mark(),
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
        anchor=serialized.anchor,
        comment=_deserialize_comment(serialized.comment),
    )


def _serialize_scalar(node: nodes.ScalarNode) -> yaml.ScalarNode:
    style = "|" if "\n" in node.value else None  # TODO: store style in node
    return yaml.ScalarNode(
        tag=node.tag,
        value=node.value,
        style=style,
        anchor=node.anchor,
        comment=_serialize_comment(node.comment),
        **_get_default_yaml_kwargs(),
    )


def _deserialize_mapping(serialized: yaml.MappingNode, path: NodePath,
                         deserialized_nodes: dict[yaml.Node, nodes.Node]) -> nodes.MappingNode:
    assert serialized.merge is None, serialized  # TODO: find out when it is not None

    items = OrderedDict()  # type: OrderedDict[str, nodes.MappingNode.Item]
    for key, value in serialized.value:
        path_key: NodePathKey = _yaml_node_as_path_key(key)
        item_path = path + (path_key,)
        key_node = _deserialize_node(key, item_path + (0,), deserialized_nodes)
        value_node = _deserialize_node(value, item_path + (1,), deserialized_nodes)
        items[path_key] = nodes.MappingNode.Item(key=key_node, value=value_node, path=item_path, path_key=path_key)

    return nodes.MappingNode(
        path=path,
        tag=serialized.tag,
        items=items,
        anchor=serialized.anchor,
        comment=_deserialize_comment(serialized.comment),
    )


def _serialize_mapping(node: nodes.MappingNode, serialized_nodes: dict[nodes.Node, yaml.Node]) -> yaml.MappingNode:
    serialized = yaml.MappingNode(
        tag=node.tag,
        value=[(_serialize_node(item.key, serialized_nodes),
                _serialize_node(item.value, serialized_nodes)) for item in node.items.values()],
        flow_style=None,  # TODO: fill
        anchor=node.anchor,
        comment=_serialize_comment(node.comment),
        **_get_default_yaml_kwargs(),
    )
    serialized.merge = None  # TODO: find out when it is not None
    return serialized


def _deserialize_sequence(serialized: yaml.SequenceNode, path: NodePath,
                          deserialized_nodes: dict[yaml.Node, nodes.Node]) -> nodes.SequenceNode:
    return nodes.SequenceNode(
        path=path,
        tag=serialized.tag,
        values=tuple(nodes.SequenceNode.Item(_deserialize_node(value, path + (i,), deserialized_nodes))
                     for i, value in enumerate(serialized.value)),
        anchor=serialized.anchor,
        comment=_deserialize_comment(serialized.comment),
    )


def _serialize_sequence(node: nodes.SequenceNode, serialized_nodes: dict[nodes.Node, yaml.Node]) -> yaml.SequenceNode:
    return yaml.SequenceNode(
        tag=node.tag,
        value=[_serialize_node(item.value, serialized_nodes) for item in node.values],
        flow_style=None,  # TODO: fill
        anchor=node.anchor,
        comment=_serialize_comment(node.comment),
        **_get_default_yaml_kwargs(),
    )


def _deserialize_node(serialized: yaml.Node, path: NodePath,
                      deserialized_nodes: dict[yaml.Node, nodes.Node]) -> nodes.Node:
    if serialized in deserialized_nodes:
        assert serialized.anchor is not None
        assert serialized.anchor == deserialized_nodes[serialized].anchor
        return nodes.ReferenceNode(path=path, referred_node=deserialized_nodes[serialized])

    node: nodes.Node
    if isinstance(serialized, yaml.ScalarNode):
        node = _deserialize_scalar(serialized, path)
    elif isinstance(serialized, yaml.MappingNode):
        node = _deserialize_mapping(serialized, path, deserialized_nodes)
    elif isinstance(serialized, yaml.SequenceNode):
        node = _deserialize_sequence(serialized, path, deserialized_nodes)
    else:
        raise TypeError(f"Unexpected yaml node {serialized}")

    deserialized_nodes[serialized] = node
    return node


def _serialize_node(node: nodes.Node, serialized_nodes: dict[nodes.Node, yaml.Node]) -> yaml.Node:
    if isinstance(node, nodes.ReferenceNode):
        assert node.referred_node.anchor is not None
        return serialized_nodes[node.referred_node]

    serialized: yaml.Node
    if isinstance(node, nodes.ScalarNode):
        serialized = _serialize_scalar(node)
    elif isinstance(node, nodes.MappingNode):
        serialized = _serialize_mapping(node, serialized_nodes)
    elif isinstance(node, nodes.SequenceNode):
        serialized = _serialize_sequence(node, serialized_nodes)
    else:
        raise Exception(f"Unexpected graph node {node}")

    serialized_nodes[node] = serialized
    return serialized


def deserialize(serialized: yaml.Node) -> nodes.Node:
    deserialized_nodes: dict[yaml.Node, nodes.Node] = {}
    return _deserialize_node(serialized, path=(), deserialized_nodes=deserialized_nodes)


def serialize(node: nodes.Node) -> yaml.Node:
    serialized_nodes: dict[nodes.Node, yaml.Node] = {}
    return _serialize_node(node, serialized_nodes)
