from collections import Counter

from ruamel import yaml
from ruamel.yaml.error import FileMark

from yaml_diff_v2 import graph


def _make_dummy_mark():
    return FileMark("<file>", 0, 0, 0)


def _convert_scalar(node: graph.ScalarNode) -> yaml.ScalarNode:
    return yaml.ScalarNode(
        tag=node.yaml_tag,
        value=node.value,
        start_mark=_make_dummy_mark(),  # Can't set None
        end_mark=_make_dummy_mark(),
        style=None,  # TODO: fill
        comment=None,
        anchor=None,
    )


def _make_map_key(key: graph.MapKey, extended: bool) -> yaml.Node:
    if not extended:
        return _convert_scalar(key.scalar)
    return yaml.SequenceNode(
        tag="tag:yaml.org,2002:seq",
        value=[
            _convert_scalar(key.scalar),
            yaml.ScalarNode(
                tag="tag:yaml.org,2002:str",
                value=key.unique_id,
                start_mark=_make_dummy_mark(),
                end_mark=_make_dummy_mark(),
            )
        ],
        start_mark=_make_dummy_mark(),
        end_mark=_make_dummy_mark(),
    )


def _convert_map(node: graph.MapNode) -> yaml.MappingNode:
    short_keys = Counter(item.key.scalar.value for item in node.items.values())

    def is_extended_key(key: graph.MapKey):
        return short_keys[key.scalar.value] > 1

    map_items = [node.items[key] for key in sorted(node.items.keys())]

    result = yaml.MappingNode(
        tag=node.yaml_tag,
        value=[
            (_make_map_key(item.key, extended=is_extended_key(item.key)), _node_to_yaml(item.value))
            for item in map_items if not item.value.is_hidden
        ],
        start_mark=_make_dummy_mark(),
        end_mark=_make_dummy_mark(),
        flow_style=None,
        comment=None,
        anchor=None,
    )
    result.merge = None  # TODO: set real value
    return result


def _node_to_yaml(node: graph.Node) -> yaml.Node:
    if isinstance(node, graph.ScalarNode):
        return _convert_scalar(node)
    if isinstance(node, graph.MapNode):
        return _convert_map(node)
    raise NotImplementedError("list")


def to_yaml(graph: graph.Graph) -> yaml.Node:
    res = _node_to_yaml(graph.root)
    return res
