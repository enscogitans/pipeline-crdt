import abc
import typing
from collections import Counter
from dataclasses import dataclass
from typing import NewType

from yaml_diff_v3 import yaml_graph
from yaml_diff_v3.yaml_graph.nodes import Comment, NodePathKey

NodeId = NewType("NodeId", str)
Timestamp = NewType("Timestamp", int)


@dataclass
class _NodeBase(abc.ABC):
    id: NodeId  # globally unique
    yaml_tag: str
    anchor: None | str
    # TODO: add list of nodes which reference this node
    yaml_path: yaml_graph.NodePath  # TODO: do not store it in the Node
    last_edit_ts: Timestamp
    is_deprecated: bool
    comment: None | Comment
    last_comment_edit_ts: Timestamp
    # is_all_parents_hidden: bool

    @property
    def is_hidden(self) -> bool:
        return self.is_deprecated  # and self.is_all_parents_hidden

    @abc.abstractmethod
    def get_children_with_path(self) -> list[tuple[NodePathKey, "Node"]]: ...

    @abc.abstractmethod
    def get_all_children(self) -> list["Node"]: ...


@dataclass
class ScalarNode(_NodeBase):
    value: str

    def get_all_children(self) -> list["Node"]:
        return []

    def get_children_with_path(self) -> list[tuple[NodePathKey, "Node"]]:
        return []


@dataclass
class MappingNode(_NodeBase):
    @dataclass
    class Item:
        id: NodeId
        key: ScalarNode
        # value is the main, key is its satellite. All operations applied to an Item modify value, not key
        value: "Node"
        sort_key: str
        last_timestamp_sort_key_edited: Timestamp

        @property
        def yaml_path(self) -> yaml_graph.NodePath:
            return self.value.yaml_path[:-1]  # TODO: make it more correct

        def get_all_children(self) -> list["Node"]:
            return [self.key, self.value]

        def get_children_with_path(self) -> list[tuple[NodePathKey, "Node"]]:
            return [(0, self.key), (1, self.value)]

    items: list[Item]

    def get_all_children(self):
        return self.items

    def get_children_with_path(self) -> list[tuple[NodePathKey, "Node"]]:
        result = []
        duplicated_keys = {
            key for key, cnt
            in Counter(item.key.value for item in self.items if not item.value.is_hidden).items()
            if cnt > 1
        }
        for item in self.items:
            if item.value.is_hidden:
                continue
            if item.key.value in duplicated_keys:
                path_key = (item.key.value, str(item.value.id))
            else:
                path_key = item.key.value
            result.append((path_key, item))
        return result


@dataclass
class SequenceNode(_NodeBase):
    @dataclass
    class Item:
        id: NodeId
        value: "Node"
        sort_key: str
        last_timestamp_sort_key_edited: Timestamp

        def get_all_children(self):
            return [self.value]

    items: list[Item]

    def get_all_children(self) -> list["Node"]:
        return self.items

    def get_children_with_path(self) -> list[tuple[NodePathKey, "Node"]]:
        items = sorted(self.items, key=lambda item: item.sort_key)
        values = [item.value for item in items if not item.value.is_hidden]
        return list(enumerate(values))


@dataclass
class ReferenceNode:
    id: NodeId
    referred_id: NodeId
    is_deprecated: bool
    yaml_path: yaml_graph.NodePath  # TODO: do not store it in the Node

    @property
    def is_hidden(self) -> bool:
        return self.is_deprecated

    def get_all_children(self) -> list["Node"]:
        return []

    def get_children_with_path(self) -> list[tuple[NodePathKey, "Node"]]:
        return []


Node = typing.Union[ScalarNode, MappingNode, SequenceNode, ReferenceNode]
