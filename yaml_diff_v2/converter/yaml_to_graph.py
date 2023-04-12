from ruamel import yaml

from yaml_diff_v2 import graph
from yaml_diff_v2.graph import ItemId
from yaml_diff_v2.meta_provider import MetaProvider


def _convert_scalar(inp: yaml.ScalarNode, path: ItemId, meta_provider: MetaProvider) -> graph.ScalarNode:
    return graph.ScalarNode(
        item_id=path,
        yaml_tag=inp.tag,
        value=inp.value,
        meta=meta_provider.get_meta(path),
    )


def _to_map_key(key: yaml.Node, item_id: ItemId, meta_provider: MetaProvider) -> graph.MapKey:
    scalar_node = _convert_scalar(
        key if isinstance(key, yaml.ScalarNode) else key.value[1].value,
        item_id, meta_provider)
    return graph.MapKey(scalar_node, scalar_node.meta.creation_key)


def _get_map_item_key(node: yaml.Node, map_path: ItemId, meta_provider: MetaProvider) -> ItemId:
    if isinstance(node, yaml.ScalarNode):
        partial_key = map_path + (node.value,)
        return meta_provider.find_full_key(partial_key)
    assert isinstance(node, yaml.SequenceNode)
    assert len(node.value) == 2
    assert isinstance(node.value[0].value, yaml.ScalarNode) and isinstance(node.value[1].value, yaml.ScalarNode)
    assert node.value[1].tag == "tag:yaml.org,2002:str"
    key = map_path + ((node.value[0].value, node.value[1].value),)
    assert key not in meta_provider.meta
    return key


def _convert_map_item(key: yaml.Node, value: yaml.Node, map_path: ItemId,
                      meta_provider: MetaProvider) -> graph.MapItem:
    item_key = _get_map_item_key(key, map_path, meta_provider)
    return graph.MapItem(
        item_id=item_key,
        key=_to_map_key(key, item_key + ("key",), meta_provider),
        value=_to_node(value, item_key + ("value",), meta_provider),
    )


def _convert_map(inp: yaml.MappingNode, path: ItemId, meta_provider: MetaProvider) -> graph.MapNode:
    assert inp.merge is None, inp.merge  # TODO: when is it not None?
    return graph.MapNode(
        item_id=path,
        yaml_tag=inp.tag,
        items=[
            _convert_map_item(key, value, path, meta_provider=meta_provider) for key, value in inp.value
        ],
        meta=meta_provider.get_meta(path),
    )


def _to_node(inp: yaml.Node, path: ItemId, meta_provider: MetaProvider) -> graph.Node:
    assert isinstance(inp, (yaml.ScalarNode, yaml.MappingNode, yaml.SequenceNode))
    if inp.id == "scalar":
        return _convert_scalar(inp, path, meta_provider)
    if inp.id == "mapping":
        return _convert_map(inp, path, meta_provider)
    if inp.id == "sequence":
        pass
    raise NotImplementedError(inp.id)


def to_graph(inp: yaml.Node, meta_provider: MetaProvider) -> graph.Graph:
    return graph.Graph(root=_to_node(inp, (), meta_provider))
