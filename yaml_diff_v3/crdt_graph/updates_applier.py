from copy import deepcopy

from yaml_diff_v3.crdt_graph.graph import Graph
from yaml_diff_v3.crdt_graph.nodes import ScalarNode, MappingNode, SequenceNode
from yaml_diff_v3.crdt_graph.updates import Update, UpdateId, EditScalarNode, AddMapItem, DeleteMapItem, EditComment, \
    EditMapItemSortKey, EditListItemSortKey, DeleteListItem, AddListItem


class UpdatesApplier:
    def __init__(self, applied_updates: set[UpdateId]):
        self.applied_updates = applied_updates

    def apply_updates(self, graph: Graph, updates: list[Update]) -> None:
        for update in updates:
            if update.update_id in self.applied_updates:
                continue
            self._apply_update(graph, update)
            self.applied_updates.add(update.update_id)

    def _apply_update(self, graph: Graph, update: Update) -> None:
        if isinstance(update, EditScalarNode):
            self._apply_edit_scalar(graph, update)
        elif isinstance(update, EditComment):
            self._apply_edit_comment(graph, update)
        elif isinstance(update, AddMapItem):
            self._apply_add_map_item(graph, update)
        elif isinstance(update, DeleteMapItem):
            self._apply_delete_map_item(graph, update)
        elif isinstance(update, EditMapItemSortKey):
            self._apply_edit_map_item_sort_key(graph, update)
        elif isinstance(update, AddListItem):
            self._apply_add_list_item(graph, update)
        elif isinstance(update, DeleteListItem):
            self._apply_delete_list_item(graph, update)
        elif isinstance(update, EditListItemSortKey):
            self._apply_edit_list_item_sort_key(graph, update)
        else:
            raise TypeError(f"Unexpected update type {update}")

    @staticmethod
    def _apply_edit_scalar(graph: Graph, update: EditScalarNode) -> None:
        node = graph.get_node(update.node_id)
        assert isinstance(node, ScalarNode)
        if node.last_edit_ts > update.timestamp:
            return
        node.yaml_tag = update.new_yaml_tag
        node.value = update.new_value
        node.last_edit_ts = update.timestamp

    @staticmethod
    def _apply_edit_comment(graph: Graph, update: EditComment) -> None:
        node = graph.get_node(update.node_id)
        assert isinstance(node, (ScalarNode, MappingNode))
        if node.last_comment_edit_ts > update.timestamp:
            return
        node.comment = update.new_comment
        node.last_comment_edit_ts = update.timestamp

    @staticmethod
    def _apply_add_map_item(graph: Graph, update: AddMapItem) -> None:
        map_node = graph.get_node(update.mapping_node_id)
        assert isinstance(map_node, MappingNode)
        map_node.items.append(deepcopy(update.new_item))

    @staticmethod
    def _apply_delete_map_item(graph: Graph, update: DeleteMapItem) -> None:
        item_value = graph.get_node(update.item_value_id)
        item_value.is_deprecated = True

    @staticmethod
    def _apply_edit_map_item_sort_key(graph: Graph, update: EditMapItemSortKey) -> None:
        item = graph.get_node(update.item_id)
        if item.last_timestamp_sort_key_edited > update.timestamp:
            return
        item.sort_key = update.new_sort_key

    @staticmethod
    def _apply_add_list_item(graph: Graph, update: AddListItem) -> None:
        list_node = graph.get_node(update.list_node_id)
        assert isinstance(list_node, SequenceNode)
        list_node.items.append(deepcopy(update.new_item))
        list_node.items.sort(key=lambda item: item.sort_key)

    @staticmethod
    def _apply_delete_list_item(graph: Graph, update: DeleteListItem) -> None:
        item_value = graph.get_node(update.item_id)
        item_value.is_deprecated = True

    @staticmethod
    def _apply_edit_list_item_sort_key(graph: Graph, update: EditListItemSortKey) -> None:
        item = graph.get_node(update.item_id)
        assert isinstance(item, SequenceNode.Item), item
        if item.last_timestamp_sort_key_edited > update.timestamp:
            return
        item.sort_key = update.new_sort_key
