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
    new_item: MappingNode.Item


@dataclass(frozen=True)
class DeleteMapItem:
    path: NodePath


Update = Union[EditScalarNode, AddMapItem, DeleteMapItem]
