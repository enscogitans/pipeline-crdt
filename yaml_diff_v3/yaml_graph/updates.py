from dataclasses import dataclass
from typing import Union

from yaml_diff_v3.yaml_graph.nodes import NodePath, MappingNode, Comment


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
class DeleteMapItem:
    path: NodePath


@dataclass(frozen=True)
class EditMapOrder:
    map_path: NodePath
    new_order: tuple[NodePath, ...]  # paths of keys that are present in both dicts


Update = Union[EditScalarNode, EditComment, AddMapItem, DeleteMapItem, EditMapOrder]
