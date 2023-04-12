from collections import defaultdict
from copy import deepcopy

from deepdiff import DeepDiff
from ruamel.yaml import CommentedSeq, CommentedMap
from ruamel.yaml.comments import CommentedBase

from yaml_diff.updates import *
from yaml_diff.updates_builder import build_yaml_updates
from yaml_diff.utils import dumps_yaml


def _is_tagged_commented_map(node: CommentedBase) -> bool:
    return isinstance(node, CommentedMap) and node.tag == "TaggedData"


def _to_tagged_commented_map(data: CommentedBase, tags: dict) -> CommentedMap:
    assert "data" not in tags
    result = CommentedMap()
    result.yaml_set_tag("TaggedData")
    result["data"] = data
    result.update(tags)
    return result


###################

def _is_multimap_node(node: CommentedBase) -> bool:
    return isinstance(node, CommentedMap) and node.tag == "MultiMap"


def _to_multimap(value: CommentedBase, session_id: str) -> CommentedMap:
    multimap_node = CommentedMap()
    multimap_node.yaml_set_tag("MultiMap")
    multimap_node[session_id] = value
    return multimap_node


###################

def _get_node(node: CommentedSeq | CommentedMap, path, session_id: str):
    # TODO: return final full path
    if _is_tagged_commented_map(node):
        return _get_node(node["data"], path, session_id)
    if _is_multimap_node(node):
        return _get_node(node[session_id], path, session_id)
    if not path:
        return node
    return _get_node(node[path[0]], path[1:], session_id)


def _get_parent(root: CommentedSeq | CommentedMap, path, session_id, *, maybe_tagged: bool):
    node = _get_node(root, path[:-1], session_id)
    if maybe_tagged and _is_tagged_commented_map(node[path[-1]]):
        return node[path[-1]]
    if _is_multimap_node(node):
        return node[session_id]
    return node


def _apply_add_iterable(yaml, upd: AddIterableItem):
    list_node = _get_parent(yaml, upd.path, maybe_tagged=False)
    assert isinstance(list_node, CommentedSeq)
    list_node.insert(len(list_node), upd.value)
    list_node.sort()  # TODO: items inside are not always comparable


def _apply_del_iterable(yaml, upd: DelIterableItem):
    parent = _get_parent(yaml, upd.path, maybe_tagged=True)
    if _is_tagged_commented_map(parent):
        parent["deprecated"] = True
    else:
        parent[upd.path[-1]] = _to_tagged_commented_map(parent[upd.path[-1]], {"deprecated": True})


def _apply_edit(yaml, upd: EditItem):
    parent = _get_parent(yaml, upd.path, upd.session_id, maybe_tagged=True)
    if "last_edit_ts" in yaml.meta[tuple(upd.path)] and yaml.meta[tuple(upd.path)]["last_edit_ts"] > upd.ts:
        return
    if _is_tagged_commented_map(parent):
        parent["data"] = upd.new_value
    else:
        parent[upd.path[-1]] = upd.new_value
    yaml.meta[tuple(upd.path)]["last_edit_ts"] = upd.ts


def _get_insert_position(iterable, new_key) -> int:
    for i, key in enumerate(iterable):
        if key > new_key:
            return i
    return len(iterable)


def _apply_add_existing_dict_key(yaml, dict_node, key, upd):
    assert key in dict_node
    if not _is_multimap_node(dict_node[key]):
        prev_meta = yaml.meta[tuple(upd.item_id)]
        del yaml.meta[tuple(upd.item_id)]
        prev_session_id = prev_meta["session_id"]
        yaml.meta[tuple(upd.item_id) + (prev_session_id,)] = prev_meta
        dict_node[key] = _to_multimap(dict_node[key], prev_session_id)
    assert upd.session_id not in dict_node[key]
    idx = _get_insert_position(dict_node[key], upd.session_id)
    dict_node[key].insert(idx, upd.session_id, upd.value)
    yaml.meta[tuple(upd.item_id) + (upd.session_id,)]["session_id"] = upd.session_id


def _apply_add_dict(root, upd):
    dict_node = _get_parent(root, upd.item_id, upd.session_id, maybe_tagged=False)
    assert isinstance(dict_node, CommentedMap)
    new_key = upd.item_id[-1]
    if new_key in dict_node:
        return _apply_add_existing_dict_key(root, dict_node, new_key, upd)

    # idx = _get_insert_position(dict_node, new_key)
    # dict_node.insert(idx, new_key, upd.value)
    dict_node[new_key] = upd.value
    root.meta[tuple(upd.item_id)]["session_id"] = upd.session_id


def _apply_del_dict(yaml, upd):
    yaml.meta[tuple(upd.item_id)]["deprecated"] = True
    yaml.meta[tuple(upd.item_id)]["data"] = _get_node(yaml, upd.item_id,
                                                      upd.session_id)  # TODO: What if it is restored and edited?
    parent = _get_parent(yaml, upd.item_id, upd.session_id, maybe_tagged=False)
    key = upd.item_id[-1]
    del parent[key]


def apply_updates(yaml, updates):
    if not hasattr(yaml, "meta"):
        setattr(yaml, "meta", defaultdict(dict))
    for upd in updates:
        if isinstance(upd, AddIterableItem):
            raise NotImplementedError(upd)
            # _apply_add_iterable(yaml, upd)
        elif isinstance(upd, DelIterableItem):
            raise NotImplementedError(upd)
            # _apply_del_iterable(yaml, upd)
        elif isinstance(upd, EditItem):
            _apply_edit(yaml, upd)
        elif isinstance(upd, AddDictItem):
            _apply_add_dict(yaml, upd)
        elif isinstance(upd, DelDictItem):
            _apply_del_dict(yaml, upd)
        else:
            raise NotImplementedError(upd)
    return yaml


# yaml_base is modified! TODO: maybe read text
def merge_yaml(yaml_base, yaml_v1, id_1, ts_1, yaml_v2, id_2, ts_2):
    updates_1 = build_yaml_updates(yaml_base, yaml_v1, session_id=id_1, ts=ts_1)
    updates_2 = build_yaml_updates(yaml_base, yaml_v2, session_id=id_2, ts=ts_2)
    updates = updates_1 + updates_2
    merged = apply_updates(yaml_base, updates)  # Can't use deepcopy(yaml_base) here!
    return merged
