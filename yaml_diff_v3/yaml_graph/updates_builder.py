from deepdiff import DeepDiff

from yaml_diff_v3.yaml_graph.nodes import Node, ScalarNode, MappingNode, ReferenceNode, Comment
from yaml_diff_v3.yaml_graph.updates import Update, EditScalarNode, AddMapItem, DeleteMapItem, EditComment


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


def _build_dictionary_item_added(items) -> list[Update]:
    updates = []
    for item in items:
        added_item = item.t2
        assert isinstance(added_item, MappingNode.Item)
        key_path = added_item.key.path
        item_path = key_path[:-1]
        map_path = item_path[:-1]
        updates.append(AddMapItem(map_path=map_path, new_item=added_item))
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


def build_updates(old_graph: Node, new_graph: Node) -> list[Update]:
    diff = DeepDiff(
        old_graph,
        new_graph,
        verbose_level=2,  # This is to see dict key's new value
        # If any of compared nodes (t1 or t2) is of this type, it is skipped.
        # TODO: what if we want to change node type from Scalar to Reference?
        exclude_types=[ReferenceNode],
    )

    updates: list[Update] = []
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
        else:
            raise NotImplementedError(operation)

    updates += _build_edit_comment(comment_edit_items)
    return updates
