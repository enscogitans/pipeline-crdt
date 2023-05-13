from collections import OrderedDict

import deepdiff.operator
from deepdiff import DeepDiff

from yaml_diff_v3.yaml_graph.nodes import Node, ScalarNode, MappingNode, ReferenceNode, Comment
from yaml_diff_v3.yaml_graph.updates import Update, EditScalarNode, AddMapItem, DeleteMapItem, EditComment, EditMapOrder


def _has_comment_parent(deepdiff_item):
    while not isinstance(deepdiff_item.t1, Node):
        if isinstance(deepdiff_item.t1, Comment) or isinstance(deepdiff_item.t2, Comment):
            return True
        deepdiff_item = deepdiff_item.up
    return False


def _get_node_parent(deepdiff_item) -> tuple[Node, Node]:
    while not isinstance(deepdiff_item.t1, Node):
        deepdiff_item = deepdiff_item.up
    assert isinstance(deepdiff_item.t1, type(deepdiff_item.t2)), "Type change should be handled by other means"
    return deepdiff_item.t1, deepdiff_item.t2


def _build_values_changed(items) -> list[EditScalarNode]:
    nodes = set()  # I need a set because same node appears several times (.tag and .value are different changes)
    for item in items:
        parent = item.up
        old_node, new_node = parent.t1, parent.t2
        assert isinstance(old_node, ScalarNode), f"Only a scalar can be edited {parent.t1}"
        assert isinstance(new_node, ScalarNode), f"Only a scalar can be edited {parent.t2}"
        assert old_node.path == new_node.path, "Should be guaranteed by DeepDiff"
        nodes.add(new_node)

    return [EditScalarNode(path=node.path, tag=node.tag, value=node.value) for node in nodes]


def _build_edit_comment(items) -> list[EditComment]:
    nodes = set()
    for item in items:
        old_node, new_node = _get_node_parent(item)
        nodes.add(new_node)
    return [EditComment(path=node.path, new_comment=node.comment) for node in nodes]


def _get_prev_item_in_ordered_dict(checked, ordered_dict: OrderedDict):
    prev_item = None
    for item in ordered_dict.values():
        if item is checked:
            return prev_item
        prev_item = item
    raise KeyError


def _get_next_item_in_ordered_dict(checked, ordered_dict: OrderedDict, key_filter):
    checked_found = False
    for key, item in ordered_dict.items():
        if not checked_found:
            if item is checked:
                checked_found = True
            continue

        if key in key_filter:
            return item

    if not checked_found:
        raise KeyError
    return None


def _build_dictionary_item_added(items) -> list[Update]:
    updates = []
    for item in items:
        added_item = item.t2
        assert isinstance(added_item, MappingNode.Item)
        key_path = added_item.key.path
        item_path = key_path[:-1]
        map_path = item_path[:-1]

        old_map, new_map = item.up.t1, item.up.t2
        assert isinstance(old_map, OrderedDict) and isinstance(new_map, OrderedDict)
        prev_item = _get_prev_item_in_ordered_dict(added_item, new_map)
        next_item = _get_next_item_in_ordered_dict(added_item, new_map, old_map.keys())

        updates.append(AddMapItem(
            map_path=map_path,
            prev_item_path=None if prev_item is None else prev_item.path,
            next_item_path=None if next_item is None else next_item.path,
            new_item=added_item,
        ))
    return updates


def _build_dictionary_item_removed(items) -> list[Update]:
    updates = []
    for item in items:
        deleted_item = item.t1
        assert isinstance(deleted_item, MappingNode.Item)
        key_path = deleted_item.key.path
        item_path = key_path[:-1]
        value_path = item_path + (1,)
        updates.append(DeleteMapItem(value_path))  # all operations with item are performed via its value
    return updates


class _DictOrderOperator(deepdiff.operator.BaseOperator):
    def __init__(self):
        super().__init__(types=[OrderedDict])  # only pairs of this type will be processed

    def give_up_diffing(self, level, diff_instance) -> bool:
        old_dict, new_dict = level.t1, level.t2
        assert isinstance(old_dict, OrderedDict) and isinstance(new_dict, OrderedDict)
        common_keys = old_dict.keys() & new_dict.keys()
        old_order = tuple(item.path for key, item in old_dict.items() if key in common_keys)
        new_order = tuple(item.path for key, item in new_dict.items() if key in common_keys)
        if old_order != new_order:
            parent = level.up
            assert isinstance(parent.t1, MappingNode) and isinstance(parent.t2, MappingNode)
            assert parent.t1.path == parent.t2.path
            diff_instance.custom_report_result(
                "edit_dict_order", level, {"map_path": parent.t2.path, "old_order": old_order, "new_order": new_order},
            )
        return False  # do not stop diffing nested objects


def _build_dictionary_edit_order(deltas) -> list[EditMapOrder]:
    return [EditMapOrder(map_path=delta["map_path"], new_order=delta["new_order"]) for delta in deltas.values()]


def build_updates(old_graph: Node, new_graph: Node) -> list[Update]:
    diff = DeepDiff(
        old_graph,
        new_graph,
        verbose_level=2,  # This is to see dict key's new value
        # If any of compared nodes (t1 or t2) is of this type, it is skipped.
        # TODO: what if we want to change node type from Scalar to Reference?
        exclude_types=[ReferenceNode],
        custom_operators=[_DictOrderOperator()],
    )

    updates: list[Update] = []
    if "edit_dict_order" in diff:
        updates += _build_dictionary_edit_order(diff["edit_dict_order"])

    comment_edit_items = []
    for operation in diff.keys():
        items = []
        for item in diff.tree[operation].items:
            if _has_comment_parent(item):
                comment_edit_items.append(item)
            else:
                items.append(item)
        if not items:
            continue

        if operation == "values_changed":
            updates += _build_values_changed(items)
        elif operation == "dictionary_item_added":
            updates += _build_dictionary_item_added(items)
        elif operation == "dictionary_item_removed":
            updates += _build_dictionary_item_removed(items)
        elif operation == "edit_dict_order":
            continue  # Was already processed (without using tree)
        else:
            raise NotImplementedError(operation)

    updates += _build_edit_comment(comment_edit_items)
    return updates
