import re
from collections import defaultdict
from dataclasses import dataclass

from deepdiff import DeepDiff

from yaml_diff_v2.graph import Graph, Item, ScalarNode, MapNode
from yaml_diff_v2.updates.types import *

"""    
    "values_changed": "Value of {diff_path} changed from {val_t1} to {val_t2}.",
    "iterable_item_added": "Item {diff_path} added to iterable.",
    "iterable_item_removed": "Item {diff_path} removed from iterable.",
    
    "dictionary_item_added": "Item {diff_path} added to dictionary.",
    "dictionary_item_removed": "Item {diff_path} removed from dictionary.",
    "type_changes": "Type of {diff_path} changed from {type_t1} to {type_t2} and value changed from {val_t1} to {val_t2}.",    
    "attribute_added": "Attribute {diff_path} added.",
    "attribute_removed": "Attribute {diff_path} removed.",
    "set_item_added": "Item root[{val_t2}] added to set.",
    "set_item_removed": "Item root[{val_t1}] removed from set.",
    "repetition_change": "Repetition change for item {diff_path}.",
"""


def _get_item_id_and_attribute(graph: Graph, path: str) -> tuple[ItemId, str]:
    def get_item_by_path(path: str):
        root = graph  # It is essential that this object is called root! It is used in the eval below
        return eval(path)

    initial_path = path
    while path:
        item = get_item_by_path(path)
        if isinstance(item, Item):
            attribute = initial_path[len(path):]
            return item.item_id, attribute
        path = path.rsplit(".", maxsplit=1)[0]

    raise Exception(f"Invalid path {initial_path}")


def _groupify_keys(path: str) -> str:
    # aba['x']['y'].sool[13][14][15].var -> aba[('x', 'y')].sool[(13, 14, 15)].var
    def inner(path_part):
        # aba['x']['y'] -> aba[('x', 'y')]
        matches = list(re.finditer(r"\[(.+?)]", path_part))
        if not matches:
            return path_part
        args = []
        for match in matches:
            args.append(match.group(1))
        tuple_string = "(" + ",".join(args) + ")"
        prefix = path_part.split("[", maxsplit=1)[0]
        return f"{prefix}[{tuple_string}]"

    return ".".join(inner(part) for part in path.split("."))


def _build_values_changed(deltas, graph: Graph, ts: Timestamp) -> list[EditScalarNode]:
    sentinel = object()

    @dataclass
    class EditInfo:
        tag = sentinel
        value = sentinel

    # TODO: read ts from delta
    edit_info_dict: dict[ItemId, EditInfo] = defaultdict(EditInfo)
    for path, delta in deltas.items():
        path = _groupify_keys(path)
        item_id, attribute = _get_item_id_and_attribute(graph, path)
        # item_id should correspond to a Scalar node
        if attribute == ".value":
            assert edit_info_dict[item_id].value is sentinel
            edit_info_dict[item_id].value = delta["new_value"]
        else:
            assert attribute == ".yaml_tag", attribute
            assert edit_info_dict[item_id].tag is sentinel
            edit_info_dict[item_id].tag = delta["new_value"]

    # Convert dict to EditScalarNode update
    updates = []
    for item_id, edit_info in edit_info_dict.items():
        node = graph.get_item_by_id(item_id)
        assert isinstance(node, ScalarNode), node
        updates.append(EditScalarNode(
            item_id=item_id,
            new_tag=edit_info.tag if edit_info.tag is not sentinel else node.yaml_tag,
            new_value=edit_info.value if edit_info.value is not sentinel else node.value,
            ts=ts,
        ))
    return updates


def _build_dictionary_item_added(deltas, old: Graph):
    updates = []
    for path, new_item in deltas.items():
        path = _groupify_keys(path)
        match = re.fullmatch(r"(.*?)(\[.+])+", path)
        assert match is not None, path
        container_path = match.group(1)
        container_item_id, _ = _get_item_id_and_attribute(old, container_path)

        assert isinstance(old.get_item_by_id(container_item_id), MapNode), "Only MapNode has dict container"
        assert isinstance(new_item, MapItem), "The only valid item in MapNode container"
        updates.append(AddMapItem(container_item_id, new_item))
    return updates


def _build_dictionary_item_removed(deltas):
    updates = []
    for path, item_to_remove in deltas.items():
        path = _groupify_keys(path)
        assert isinstance(item_to_remove, MapItem), "Only MapNode has dict container"
        updates.append(DelMapItem(item_to_remove.item_id))
    return updates


def build_updates(old: Graph, new: Graph, ts: Timestamp):
    diff = DeepDiff(
        old, new,
        verbose_level=2,  # verbose level is to see dict key's new value
        ignore_order=True,  # Will handle swaps by other means
    )
    updates = []
    for operation, deltas in diff.items():
        if operation == "values_changed":
            updates += _build_values_changed(deltas, old, ts)
        elif operation == "dictionary_item_added":
            updates += _build_dictionary_item_added(deltas, old)
        elif operation == "dictionary_item_removed":
            updates += _build_dictionary_item_removed(deltas)
        else:
            raise NotImplementedError(operation)
    return updates
