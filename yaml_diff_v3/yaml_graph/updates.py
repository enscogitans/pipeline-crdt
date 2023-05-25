from dataclasses import dataclass
from typing import Union

from yaml_diff_v3.yaml_graph.nodes import NodePath, MappingNode, Comment, SequenceNode


@dataclass(frozen=True)
class EditScalarNode:
    path: NodePath
    tag: str
    value: str


@dataclass(frozen=True)
class EditComment:
    path: NodePath
    new_comment: Comment


@dataclass(frozen=True)
class AddMapItem:
    map_path: NodePath
    prev_item_path: None | NodePath  # prev item is an item in the new mapping
    next_item_path: None | NodePath  # next item should present in old mapping
    new_item: MappingNode.Item


@dataclass(frozen=True)
class AddListItem:
    list_path: NodePath
    insertion_index: int
    new_item: SequenceNode.Item


@dataclass(frozen=True)
class DeleteMapItem:
    path: NodePath


@dataclass(frozen=True)
class DeleteListItem:
    path: NodePath


@dataclass(frozen=True)
class EditMapOrder:
    map_path: NodePath
    new_order: tuple[NodePath, ...]  # paths of keys that are present in both dicts


@dataclass(frozen=True)
class EditListOrder:
    list_path: NodePath
    new_order: tuple[int, ...]  # permutation of values from old list which present in a new list


Update = Union[EditScalarNode, EditComment, AddMapItem, DeleteMapItem, AddListItem, DeleteListItem,
               EditMapOrder, EditListOrder]
