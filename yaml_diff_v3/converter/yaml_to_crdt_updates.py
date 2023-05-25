import yaml_diff_v3.yaml_graph.updates as yaml
from yaml_diff_v3.converter.new_yaml_node_to_crdt_node import make_new_crdt_mapping_item_from_yaml, \
    make_new_crdt_node_from_yaml
from yaml_diff_v3.crdt_graph.graph import Graph
from yaml_diff_v3.crdt_graph.nodes import Node, Timestamp, NodeId, MappingNode, SequenceNode
from yaml_diff_v3.crdt_graph.updates import SessionId, EditScalarNode, EditComment, UpdateId, Update, AddMapItem, \
    DeleteMapItem, EditMapItemSortKey, EditListItemSortKey, AddListItem, DeleteListItem
from yaml_diff_v3.utils import make_unique_id


def _convert_edit_scalar_node(yaml_update: yaml.EditScalarNode, session_id: SessionId, ts: Timestamp,
                              path_to_node_mapping: dict[yaml.NodePath, Node | MappingNode.Item]) -> EditScalarNode:
    return EditScalarNode(
        session_id=session_id,
        timestamp=ts,
        update_id=UpdateId(make_unique_id()),
        node_id=path_to_node_mapping[yaml_update.path].id,
        new_yaml_tag=yaml_update.tag,
        new_value=yaml_update.value,
    )


def _convert_edit_comment(yaml_update: yaml.EditComment, session_id: SessionId, ts: Timestamp,
                          path_to_node_mapping: dict[yaml.NodePath, Node | MappingNode.Item]) -> EditComment:
    return EditComment(
        session_id=session_id,
        timestamp=ts,
        update_id=UpdateId(make_unique_id()),
        node_id=path_to_node_mapping[yaml_update.path].id,
        new_comment=yaml_update.new_comment,
    )


def _convert_add_map_item(yaml_update: yaml.AddMapItem, session_id: SessionId, ts: Timestamp,
                          path_to_node_mapping: dict[yaml.NodePath, Node | MappingNode.Item],
                          map_items_sort_keys: dict[yaml.NodePath, str]) -> AddMapItem:
    prev_item_sort_key = None if yaml_update.prev_item_path is None else map_items_sort_keys[yaml_update.prev_item_path]
    next_item_sort_key = None if yaml_update.next_item_path is None else map_items_sort_keys[yaml_update.next_item_path]

    sort_key = _make_sort_key_between(prev_item_sort_key, next_item_sort_key)
    map_items_sort_keys[yaml_update.new_item.path] = sort_key

    new_item = make_new_crdt_mapping_item_from_yaml(yaml_update.new_item, ts, sort_key, path_to_node_mapping)
    return AddMapItem(
        session_id=session_id,
        timestamp=ts,
        update_id=UpdateId(make_unique_id()),
        mapping_node_id=path_to_node_mapping[yaml_update.map_path].id,
        new_item=new_item,
    )


def _convert_add_list_item(yaml_update: yaml.AddListItem, session_id: SessionId, ts: Timestamp,
                           path_to_node_mapping: dict[yaml.NodePath, Node | MappingNode.Item],
                           list_items_sort_keys: dict[yaml.NodePath, list[str]]) -> AddListItem:
    list_sort_keys = list_items_sort_keys[yaml_update.list_path]
    idx = yaml_update.insertion_index
    # insert this element between list[idx - 1] and list[idx]
    prev_sort_key = list_sort_keys[idx - 1] if idx > 0 else None
    next_sort_key = list_sort_keys[idx] if idx < len(list_sort_keys) else None

    sort_key = _make_sort_key_between(prev_sort_key, next_sort_key)
    list_sort_keys.insert(idx, sort_key)
    assert all(list_sort_keys[i - 1] < list_sort_keys[i] for i in range(1, len(list_sort_keys)))

    new_item = SequenceNode.Item(
        id=NodeId(make_unique_id()),
        value=make_new_crdt_node_from_yaml(yaml_update.new_item.value, ts),
        sort_key=sort_key,
        last_timestamp_sort_key_edited=ts,
    )
    return AddListItem(
        session_id=session_id,
        timestamp=ts,
        update_id=UpdateId(make_unique_id()),
        list_node_id=path_to_node_mapping[yaml_update.list_path].id,
        new_item=new_item,
    )


def _convert_delete_map_item(yaml_update: yaml.DeleteMapItem, session_id: SessionId, ts: Timestamp,
                             path_to_node_mapping: dict[yaml.NodePath, Node | MappingNode.Item]) -> DeleteMapItem:
    value_node = path_to_node_mapping[yaml_update.path]
    return DeleteMapItem(
        session_id=session_id,
        timestamp=ts,
        update_id=UpdateId(make_unique_id()),
        item_value_id=value_node.id,
    )


def _convert_delete_list_item(yaml_update: yaml.DeleteListItem, session_id: SessionId, ts: Timestamp,
                              path_to_node_mapping: dict[yaml.NodePath, Node | MappingNode.Item],
                              list_items_sort_keys: dict[yaml.NodePath, list[str]]) -> DeleteListItem:
    node = path_to_node_mapping[yaml_update.path]
    item = path_to_node_mapping[yaml_update.path[:-1]].items[yaml_update.path[-1]]
    assert isinstance(item, SequenceNode.Item)

    old_idx = yaml_update.path[-1]
    assert isinstance(old_idx, int)
    assert list_items_sort_keys[yaml_update.path[:-1]][old_idx] == item.sort_key
    list_items_sort_keys[yaml_update.path[:-1]][old_idx] = None

    return DeleteListItem(
        session_id=session_id,
        timestamp=ts,
        update_id=UpdateId(make_unique_id()),
        item_id=node.id,
    )


def _get_longest_chain_satisfying_old_order(old_order: list[NodeId], new_order: list[NodeId]) -> list[NodeId]:
    old_index = {node_id: index for index, node_id in enumerate(old_order)}
    permutation = [old_index[node_id] for node_id in new_order]
    # In these terms we need to find the longest increasing subsequence in the permutation
    # Use dynamic programming
    max_lengths = [1] * len(permutation)  # length of LIS if it ends in position i
    prevs = [None] * len(permutation)
    for i in range(1, len(permutation)):
        for j in range(i):
            if permutation[i] > permutation[j] and max_lengths[i] < max_lengths[j] + 1:
                max_lengths[i] = max_lengths[j] + 1
                prevs[i] = j
    best_idx = None
    for i, length in enumerate(max_lengths):
        if best_idx is None or max_lengths[best_idx] < length:
            best_idx = i

    reversed_chain = [best_idx]  # indices of permutation array
    while True:
        prev = prevs[reversed_chain[-1]]
        if prev is None:
            break
        reversed_chain.append(prev)
    return [new_order[idx] for idx in reversed_chain[::-1]]


def _make_sort_key_between(left_key: None | str, right_key: None | str) -> str:
    if left_key is None:
        left_key = "0R"
    if right_key is None:
        right_key = "9R"
    # It implies that all existing keys should start with, for example, "1"

    result: str
    if right_key.startswith(left_key):  # strict prefix
        result = right_key[:-1] + "L" + make_unique_id() + "R"
    else:
        result = left_key + make_unique_id() + "R"

    assert left_key < result < right_key
    return result


def _convert_edit_map_order(
        yaml_update: yaml.EditMapOrder, session_id: SessionId, ts: Timestamp,
        path_to_node_mapping: dict[yaml.NodePath, Node | MappingNode.Item],
        map_items_sort_keys: dict[yaml.NodePath, str]) -> list[EditMapItemSortKey]:
    result: list[EditMapItemSortKey] = []

    new_order_items = [path_to_node_mapping[path] for path in yaml_update.new_order]

    old_order_ids = [item.id for item in sorted(new_order_items, key=lambda item: item.sort_key)]
    new_order_ids = [item.id for item in new_order_items]
    longest_chain = set(_get_longest_chain_satisfying_old_order(old_order_ids, new_order_ids))

    prev_sort_key = None
    for i, item in enumerate(new_order_items):
        if item.id in longest_chain:
            prev_sort_key = item.sort_key
            continue

        next_sort_key: None | str = None
        for next_item in new_order_items[i + 1:]:
            if next_item.id in longest_chain:
                next_sort_key = next_item.sort_key
                break

        new_sort_key = _make_sort_key_between(prev_sort_key, next_sort_key)
        assert item.yaml_path in map_items_sort_keys
        map_items_sort_keys[item.yaml_path] = new_sort_key
        result.append(EditMapItemSortKey(
            session_id=session_id,
            timestamp=ts,
            update_id=UpdateId(make_unique_id()),
            item_id=item.id,
            new_sort_key=new_sort_key,
        ))
        prev_sort_key = new_sort_key

    return result


def _convert_edit_list_order(
        yaml_update: yaml.EditListOrder, session_id: SessionId, ts: Timestamp,
        path_to_node_mapping: dict[yaml.NodePath, Node | MappingNode.Item],
        list_items_sort_keys: dict[yaml.NodePath, list[str]]) -> list[EditListItemSortKey]:
    result: list[EditListItemSortKey] = []

    new_order_items = [path_to_node_mapping[yaml_update.list_path].items[idx] for idx in yaml_update.new_order]
    old_order_items = [item for item in sorted(new_order_items, key=lambda item: item.sort_key)]

    # They contain only common items
    assert list_items_sort_keys[yaml_update.list_path] == [item.sort_key for item in old_order_items]

    new_order_ids = [item.id for item in new_order_items]
    old_order_ids = [item.id for item in old_order_items]
    longest_chain = set(_get_longest_chain_satisfying_old_order(old_order_ids, new_order_ids))

    prev_sort_key = None
    for i, item in enumerate(new_order_items):
        if item.id in longest_chain:
            prev_sort_key = item.sort_key
            continue

        next_sort_key: None | str = None
        for next_item in new_order_items[i + 1:]:
            if next_item.id in longest_chain:
                next_sort_key = next_item.sort_key
                break

        new_sort_key = _make_sort_key_between(prev_sort_key, next_sort_key)

        result.append(EditListItemSortKey(
            session_id=session_id,
            timestamp=ts,
            update_id=UpdateId(make_unique_id()),
            item_id=item.id,
            new_sort_key=new_sort_key,
        ))

        old_idx = list_items_sort_keys[yaml_update.list_path].index(item.sort_key)
        list_items_sort_keys[yaml_update.list_path][old_idx] = new_sort_key
        list_items_sort_keys[yaml_update.list_path].sort()

        prev_sort_key = new_sort_key

    return result


def make_crdt_updates_from_yaml_updates(yaml_updates: list[yaml.Update], session_id: SessionId,
                                        ts: Timestamp, graph: Graph) -> list[Update]:
    result = []
    path_to_node_mapping = graph.get_path_to_node_mapping()

    # Handle sort keys first because they will be used in AddMapItem / AddListItem
    map_items_sort_keys: dict[yaml.NodePath, str] = {
        path: item.sort_key for path, item in path_to_node_mapping.items()
        if isinstance(item, MappingNode.Item)
    }
    for yaml_update in yaml_updates:
        if isinstance(yaml_update, yaml.EditMapOrder):
            result += _convert_edit_map_order(yaml_update, session_id, ts, path_to_node_mapping, map_items_sort_keys)

    # list path -> its visible elements' sort keys
    list_items_sort_keys: dict[yaml.NodePath, list[str]] = {
        list_path: sorted([item.sort_key for item in list_node.items if not item.value.is_hidden])
        for list_path, list_node in path_to_node_mapping.items() if isinstance(list_node, SequenceNode)
    }
    for yaml_update in yaml_updates:
        if isinstance(yaml_update, yaml.DeleteListItem):
            update = _convert_delete_list_item(yaml_update, session_id, ts, path_to_node_mapping, list_items_sort_keys)
            result.append(update)
    list_items_sort_keys = {
        # remove keys of deleted items
        list_path: [sort_key for sort_key in sort_keys if sort_key is not None]
        for list_path, sort_keys in list_items_sort_keys.items()
    }
    for yaml_update in yaml_updates:
        if isinstance(yaml_update, yaml.EditListOrder):
            result += _convert_edit_list_order(yaml_update, session_id, ts, path_to_node_mapping, list_items_sort_keys)
    add_list_items_updates = sorted(
        [upd for upd in yaml_updates if isinstance(upd, yaml.AddListItem)],
        key=lambda upd: (upd.list_path, upd.insertion_index)
    )
    for yaml_update in add_list_items_updates:
        result.append(_convert_add_list_item(yaml_update, session_id, ts, path_to_node_mapping, list_items_sort_keys))

    for yaml_update in yaml_updates:
        if isinstance(yaml_update, (yaml.EditMapOrder, yaml.DeleteListItem, yaml.EditListOrder, yaml.AddListItem)):
            continue

        converted: Update
        if isinstance(yaml_update, yaml.EditScalarNode):
            converted = _convert_edit_scalar_node(yaml_update, session_id, ts, path_to_node_mapping)
        elif isinstance(yaml_update, yaml.EditComment):
            converted = _convert_edit_comment(yaml_update, session_id, ts, path_to_node_mapping)
        elif isinstance(yaml_update, yaml.AddMapItem):
            converted = _convert_add_map_item(yaml_update, session_id, ts, path_to_node_mapping, map_items_sort_keys)
        elif isinstance(yaml_update, yaml.DeleteMapItem):
            converted = _convert_delete_map_item(yaml_update, session_id, ts, path_to_node_mapping)
        else:
            raise NotImplementedError(f"Unexpected yaml update type {yaml_update}")
        result.append(converted)
    return result
