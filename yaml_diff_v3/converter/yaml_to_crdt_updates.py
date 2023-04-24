import yaml_diff_v3.yaml_graph.updates as yaml
from yaml_diff_v3.converter.new_yaml_node_to_crdt_node import make_new_crdt_mapping_item_from_yaml
from yaml_diff_v3.crdt_graph.graph import Graph
from yaml_diff_v3.crdt_graph.nodes import Node, Timestamp
from yaml_diff_v3.crdt_graph.updates import SessionId, EditScalarNode, UpdateId, Update, AddMapItem, DeleteMapItem
from yaml_diff_v3.utils import make_unique_id


def _convert_edit_scalar_node(yaml_update: yaml.EditScalarNode, session_id: SessionId, ts: Timestamp,
                              path_to_node_mapping: dict[yaml.NodePath, Node]) -> EditScalarNode:
    return EditScalarNode(
        session_id=session_id,
        timestamp=ts,
        update_id=UpdateId(make_unique_id()),
        node_id=path_to_node_mapping[yaml_update.path].id,
        new_yaml_tag=yaml_update.tag,
        new_value=yaml_update.value,
    )


def _convert_add_map_item(yaml_update: yaml.AddMapItem, session_id: SessionId, ts: Timestamp,
                          path_to_node_mapping: dict[yaml.NodePath, Node]) -> AddMapItem:
    new_item = make_new_crdt_mapping_item_from_yaml(yaml_update.new_item, ts, path_to_node_mapping)
    return AddMapItem(
        session_id=session_id,
        timestamp=ts,
        update_id=UpdateId(make_unique_id()),
        mapping_node_id=path_to_node_mapping[yaml_update.map_path].id,
        new_item=new_item,
    )


def _convert_delete_map_item(yaml_update: yaml.DeleteMapItem, session_id: SessionId, ts: Timestamp,
                             path_to_node_mapping: dict[yaml.NodePath, Node]) -> DeleteMapItem:
    value_node = path_to_node_mapping[yaml_update.path]
    return DeleteMapItem(
        session_id=session_id,
        timestamp=ts,
        update_id=UpdateId(make_unique_id()),
        item_value_id=value_node.id,
    )


def make_crdt_updates_from_yaml_updates(yaml_updates: list[yaml.Update], session_id: SessionId,
                                        ts: Timestamp, graph: Graph) -> list[Update]:
    result = []
    path_to_node_mapping = graph.get_path_to_node_mapping()
    for yaml_update in yaml_updates:
        converted: Update
        if isinstance(yaml_update, yaml.EditScalarNode):
            converted = _convert_edit_scalar_node(yaml_update, session_id, ts, path_to_node_mapping)
        elif isinstance(yaml_update, yaml.AddMapItem):
            converted = _convert_add_map_item(yaml_update, session_id, ts, path_to_node_mapping)
        elif isinstance(yaml_update, yaml.DeleteMapItem):
            converted = _convert_delete_map_item(yaml_update, session_id, ts, path_to_node_mapping)
        else:
            raise NotImplementedError(f"Unexpected yaml update type {yaml_update}")
        result.append(converted)
    return result
