import re

from deepdiff import DeepDiff
from deepdiff.helper import NotPresent
from ruamel.yaml import CommentedMap

from yaml_diff.updates import *

"""    
    "values_changed": "Value of {diff_path} changed from {val_t1} to {val_t2}.",
    "type_changes": "Type of {diff_path} changed from {type_t1} to {type_t2} and value changed from {val_t1} to {val_t2}.",
    "dictionary_item_added": "Item {diff_path} added to dictionary.",
    "dictionary_item_removed": "Item {diff_path} removed from dictionary.",
    
    "iterable_item_added": "Item {diff_path} added to iterable.",
    "iterable_item_removed": "Item {diff_path} removed from iterable.",
    
    "attribute_added": "Attribute {diff_path} added.",
    "attribute_removed": "Attribute {diff_path} removed.",
    "set_item_added": "Item root[{val_t2}] added to set.",
    "set_item_removed": "Item root[{val_t1}] removed from set.",
    "repetition_change": "Repetition change for item {diff_path}.",
"""


def _make_path(path_str: str) -> list[str | int]:
    path = []
    for part in re.findall(r"\[('\w+'|\d+)]", path_str):
        if part.startswith("'"):
            path.append(part[1:-1])
        else:
            path.append(int(part))
    return path


def _build_attribute_removed(deltas):
    ignored_suffixes = ["._yaml_anchor", "._yaml_comment", "._yaml_format", "._yaml_line_col"]
    for path in deltas:
        if any(path.endswith(suffix) for suffix in ignored_suffixes):
            pass
        else:
            raise NotImplementedError(path)
    return []


def _build_iterable_item_added(deltas):
    return [AddIterableItem(_make_path(path), new_value) for path, new_value in deltas.items()]


def _build_iterable_item_removed(deltas):
    return [DelIterableItem(_make_path(path)) for path in deltas.keys()]


def _build_values_changed(deltas, session_id, ts):
    return [EditItem(_make_path(path), value_info["new_value"], session_id, ts) for path, value_info in deltas.items()]


def _build_dictionary_item_added(deltas, session_id):
    return [AddDictItem(_make_path(path), new_value, session_id) for path, new_value in deltas.items()]


def _build_dictionary_item_removed(deltas, session_id):
    return [DelDictItem(_make_path(path), session_id) for path in deltas.keys()]


def _has_merge_in_path(root, path_str):
    """
        Key:
          <<: *ptr  # dereferenced values are considered merged
    """
    def inner(node, path):
        if not path:
            return False
        key = path[0]
        if isinstance(node, CommentedMap) and any(key in merged_dict for _, merged_dict in node.merge):
            return True
        return inner(node[key], path[1:])
    return inner(root, _make_path(path_str))


def _has_anchor(node, anchors_met):
    """
        Key: *ptr  # in this case Key has anchor 'ptr'
    """
    if hasattr(node, "anchor") and node.anchor.value is not None:
        if node.anchor.value not in anchors_met:
            anchors_met.add(node.anchor.value)
        else:
            return True
    return False


def _make_exclude_callback(root_1, root_2):
    root_idx = 1
    anchors_met_1 = set()
    anchors_met_2 = set()

    def should_exclude(node, path_str):
        nonlocal root_idx, anchors_met_1, anchors_met_2
        root = root_1 if root_idx == 1 else root_2
        anchors_met = anchors_met_1 if root_idx == 1 else anchors_met_2
        result = not isinstance(node, NotPresent) and \
                 (_has_anchor(node, anchors_met) or _has_merge_in_path(root, path_str))
        root_idx = 2 if (root_idx == 1 and not result) else 1
        return result

    return should_exclude


def build_yaml_updates(old, new, session_id: str, ts: int):
    diff = DeepDiff(
        old, new,
        verbose_level=2,  # verbose level is to see dict key's new value
        exclude_obj_callback=_make_exclude_callback(old, new),
    )
    updates = []
    for operation, deltas in diff.items():
        if operation == "iterable_item_added":
            updates += _build_iterable_item_added(deltas)
        elif operation == "iterable_item_removed":
            updates += _build_iterable_item_removed(deltas)
        elif operation == "attribute_removed":
            updates += _build_attribute_removed(deltas)
        elif operation in ("values_changed", "type_changes"):
            updates += _build_values_changed(deltas, session_id, ts)
        elif operation == "dictionary_item_added":
            updates += _build_dictionary_item_added(deltas, session_id)
        elif operation == "dictionary_item_removed":
            updates += _build_dictionary_item_removed(deltas, session_id)
        else:
            raise NotImplementedError(operation)
    return updates
