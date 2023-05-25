import re
from collections import OrderedDict, defaultdict

import deepdiff.operator
from deepdiff import DeepDiff

from yaml_diff_v3.yaml_graph.nodes import Node, ScalarNode, MappingNode, ReferenceNode, Comment, SequenceNode
from yaml_diff_v3.yaml_graph.updates import Update, EditScalarNode, AddMapItem, DeleteMapItem, EditComment, \
    EditMapOrder, AddListItem, EditListOrder, DeleteListItem


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
        if isinstance(item.t1, SequenceNode.Item):
            old_node = item.t1.value
            new_node = item.t2.value
        else:
            parent = item.up
            old_node, new_node = parent.t1, parent.t2

        assert isinstance(old_node, ScalarNode), f"Only a scalar can be edited {old_node}"
        assert isinstance(new_node, ScalarNode), f"Only a scalar can be edited {new_node}"
        nodes.add((old_node.path, new_node))

    return [EditScalarNode(path=old_node_path, tag=node.tag, value=node.value) for old_node_path, node in nodes]


def _build_edit_comment(items) -> list[EditComment]:
    nodes = set()
    for item in items:
        old_node, new_node = _get_node_parent(item)
        nodes.add((old_node.path, new_node))
    return [EditComment(path=old_node_path, new_comment=node.comment) for old_node_path, node in nodes]


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
        map_path = item_path[:-1]  # TODO: use t1 path

        old_map, new_map = item.up.t1, item.up.t2
        assert isinstance(old_map, OrderedDict) and isinstance(new_map, OrderedDict)
        prev_item = _get_prev_item_in_ordered_dict(added_item, new_map)
        next_item = _get_next_item_in_ordered_dict(added_item, new_map, old_map.keys())

        updates.append(AddMapItem(
            map_path=map_path,
            prev_item_path=None if prev_item is None else prev_item.path,  # TODO: use relative path (indices/keys)
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


def _build_list_item_removed(items) -> list[Update]:
    updates = []
    for item in items:
        deleted_item = item.t1
        assert isinstance(deleted_item, SequenceNode.Item)
        path = deleted_item.value.path
        updates.append(DeleteListItem(path))
    return updates


def _get_index(path: str) -> int:
    # root.values[1] -> 1
    match = re.fullmatch(r".+\[(\d+)]", path)
    assert match is not None, path
    return int(match.group(1))


def _build_list_item_added(items) -> list[Update]:
    updates = []
    for item in items:
        added_item = item.t2
        assert isinstance(added_item, SequenceNode.Item)
        insertion_index = _get_index(item.path())
        old_list = item.up.up.t1  # Item -> tuple of items -> SequenceNode
        assert isinstance(old_list, SequenceNode)
        updates.append(AddListItem(
            list_path=old_list.path,
            insertion_index=insertion_index,
            new_item=added_item,
        ))
    return updates


def _match_mapping_order(old_mapping: MappingNode, new_mapping: MappingNode):
    # TODO: do not duplicate code
    common_keys = old_mapping.items.keys() & new_mapping.items.keys()
    old_order = tuple(key for key, item in old_mapping.items.items() if key in common_keys)
    new_order = tuple(key for key, item in new_mapping.items.items() if key in common_keys)
    return old_order, new_order


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
            # assert parent.t1.path == parent.t2.path
            diff_instance.custom_report_result(
                "edit_dict_order", level, {"map_path": parent.t1.path, "old_order": old_order, "new_order": new_order},
            )
        return False  # do not stop diffing nested objects


class _ListOrderOperator(deepdiff.operator.BaseOperator):
    def __init__(self):
        super().__init__(types=[SequenceNode, SequenceNode.Item])
        # all pairs of old SequenceNode and corresponding new SequenceNode
        self.compared_nodes: list[tuple[SequenceNode, SequenceNode]] = []
        # id(edited item) -> original item
        self.original_items: dict[int, SequenceNode.Item] = {}
        self.root_diff = None

    def give_up_diffing(self, level, diff_instance) -> bool:
        if self.root_diff is None:
            self.root_diff = diff_instance

        if diff_instance is not self.root_diff:  # This is inner deepdiff call. Skip it
            return False

        if isinstance(level.t1, SequenceNode):
            old_list, new_list = level.t1, level.t2
            assert isinstance(old_list, SequenceNode) and isinstance(new_list, SequenceNode)
            self.compared_nodes.append((old_list, new_list))
        else:
            old_item, edited_item = level.t1, level.t2
            assert isinstance(old_item, SequenceNode.Item) and isinstance(edited_item, SequenceNode.Item)
            if id(edited_item) in self.original_items:
                assert self.original_items[id(edited_item)] is old_item
            elif isinstance(old_item.value, type(edited_item.value)):
                self.original_items[id(edited_item)] = old_item
        return False

    def _match_list_items(self, old_list: SequenceNode, new_list: SequenceNode, hashes) -> list[tuple[int, int]]:
        hash_to_old_index = defaultdict(list)
        for i, old_item in enumerate(old_list.values):
            hash_to_old_index[hashes[old_item]].append(i)
        hash_to_old_index = {k: v[::-1] for k, v in hash_to_old_index.items()}

        result = []
        for j, new_item in enumerate(new_list.values):
            new_item_hash = hashes[new_item]
            if id(new_item) in self.original_items:
                old_item = self.original_items[id(new_item)]
                old_item_hash = hashes[old_item]
            elif new_item_hash in hash_to_old_index:
                old_item_hash = new_item_hash
            else:  # newly added item
                continue
            matching_old_indices = hash_to_old_index[old_item_hash]
            i = matching_old_indices.pop()  # get the smallest index
            if not matching_old_indices:
                del hash_to_old_index[old_item_hash]
            result.append((i, j))
        return result

    def _match_lists_recursively(self, old_list: SequenceNode, new_list: SequenceNode, hashes, used_pairs: set):
        if (id(old_list), id(new_list)) in used_pairs:
            return []
        used_pairs.add((id(old_list), id(new_list)))
        pairs = self._match_list_items(old_list, new_list, hashes)
        result = []
        if not all(pairs[i - 1] < pairs[i] for i in range(1, len(pairs))):
            # If both sequences are ascending, no permutations were made. Only insertions and deletions
            result.append(EditListOrder(list_path=old_list.path, new_order=tuple(i for i, j in pairs)))
        for i, j in pairs:
            old_item: SequenceNode.Item = old_list.values[i]
            new_item: SequenceNode.Item = new_list.values[j]
            if not isinstance(old_item.value, type(new_item.value)):
                continue  # type was changed, this is not a match. Process it outside as delete + add
            if isinstance(old_item.value, SequenceNode):
                result += self._match_lists_recursively(old_item.value, new_item.value, hashes, used_pairs)
            elif isinstance(old_item.value, MappingNode):
                result += self._match_mappings_recursively(old_item.value, new_item.value, hashes, used_pairs)
        return result

    def _match_mappings_recursively(self, old_mapping: MappingNode,
                                    new_mapping: MappingNode, hashes, used_pairs: set):
        if (id(old_mapping), id(new_mapping)) in used_pairs:
            return []
        used_pairs.add((id(old_mapping), id(new_mapping)))
        old_key_order, new_key_order = _match_mapping_order(old_mapping, new_mapping)
        result = []
        if old_key_order != new_key_order:
            result.append(EditMapOrder(
                map_path=old_mapping.path,
                new_order=tuple(old_mapping.items[key].path for key in new_key_order),
            ))
        for key in new_key_order:
            old_item: MappingNode.Item = old_mapping.items[key]
            new_item: MappingNode.Item = new_mapping.items[key]
            if isinstance(old_item.value, SequenceNode):
                assert isinstance(new_item.value, SequenceNode)
                result += self._match_lists_recursively(old_item.value, new_item.value, hashes, used_pairs)
            elif isinstance(old_item.value, MappingNode):
                assert isinstance(new_item.value, MappingNode)
                result += self._match_mappings_recursively(old_item.value, new_item.value, hashes, used_pairs)
        return result

    def make_edit_order_updates(self, hashes: dict) -> list[EditListOrder | EditMapOrder]:
        result = []
        used_pairs = set()
        for old_list, new_list in self.compared_nodes:
            result += self._match_lists_recursively(old_list, new_list, hashes, used_pairs)
        return result


def _build_dictionary_edit_order(deltas) -> list[EditMapOrder]:
    return [EditMapOrder(map_path=delta["map_path"], new_order=delta["new_order"]) for delta in deltas.values()]


def _fix_type_changes(diff: deepdiff.DeepDiff) -> None:
    for item in diff.tree["type_changes"]:
        if _has_comment_parent(item):
            continue
        parent = item.up
        old_value = parent.t1
        new_value = parent.t2
        assert isinstance(new_value, SequenceNode.Item)
        assert isinstance(old_value, SequenceNode.Item)
        diff.custom_report_result("iterable_item_removed", parent)
        diff.custom_report_result("iterable_item_added", parent)
        diff.tree["type_changes"].discard(item)


def build_updates(old_graph: Node, new_graph: Node) -> list[Update]:
    def exclude_object_diff(value, level_path) -> bool:
        return level_path.endswith(".path")  # TODO: become agnostic to variable name

    list_order_operator = _ListOrderOperator()
    hashes = {}
    diff = DeepDiff(
        old_graph,
        new_graph,
        verbose_level=2,  # This is to see dict key's new value
        # If any of compared nodes (t1 or t2) is of this type, it is skipped.
        # TODO: what if we want to change node type from Scalar to Reference?
        exclude_types=[ReferenceNode],
        exclude_obj_callback=exclude_object_diff,
        custom_operators=[_DictOrderOperator(), list_order_operator],
        hashes=hashes,
        ignore_order=True,
    )

    _fix_type_changes(diff)

    updates: list[Update] = list_order_operator.make_edit_order_updates(hashes)
    if "edit_dict_order" in diff:
        updates += _build_dictionary_edit_order(diff["edit_dict_order"])

    comment_edit_items = []
    for operation in diff.tree.keys():
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
        elif operation == "iterable_item_added":
            updates += _build_list_item_added(items)
        elif operation == "iterable_item_removed":
            updates += _build_list_item_removed(items)
        elif operation == "edit_dict_order":
            continue  # Was already processed (without using tree)
        else:
            raise NotImplementedError(operation)

    updates += _build_edit_comment(comment_edit_items)
    return updates
