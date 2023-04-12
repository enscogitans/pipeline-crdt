from yaml_diff_v2.graph import Graph, ScalarNode, MapNode
from yaml_diff_v2.updates.types import *


def _apply_edit_scalar(graph: Graph, update: EditScalarNode):
    graph.edit_scalar_node(update.item_id, update.new_value, update.new_tag, update.ts)


def _apply_add_map_item(graph: Graph, update: AddMapItem):
    graph.add_map_item(update.container_item_id, update.new_node)


def _apply_del_map_item(graph: Graph, update: DelMapItem):
    graph.del_map_item(update.item_id)


def apply_updates(graph: Graph, updates: list[Update]):
    for update in updates:
        if isinstance(update, EditScalarNode):
            _apply_edit_scalar(graph, update)
        elif isinstance(update, AddMapItem):
            _apply_add_map_item(graph, update)
        elif isinstance(update, DelMapItem):
            _apply_del_map_item(graph, update)
        else:
            raise NotImplementedError(type(update))
