import abc
import typing
from dataclasses import dataclass
from typing import NewType

from yaml_diff_v3 import yaml_graph

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
    # is_all_parents_hidden: bool

    @property
    def is_hidden(self) -> bool:
        return self.is_deprecated  # and self.is_all_parents_hidden

    @abc.abstractmethod
    def get_children(self) -> list["Node"]: ...


@dataclass
class ScalarNode(_NodeBase):
    value: str

    def get_children(self) -> list["Node"]:
        return []


@dataclass
class MappingNode(_NodeBase):
    @dataclass
    class Item:
        key: ScalarNode
        # value is the main, key is its satellite. All operations applied to an Item modify value, not key
        value: "Node"

    items: list[Item]

    def get_children(self) -> list["Node"]:
        return [item.value for item in self.items]


@dataclass
class ReferenceNode:
    id: NodeId
    referred_id: NodeId
    is_deprecated: bool
    yaml_path: yaml_graph.NodePath  # TODO: do not store it in the Node

    @property
    def is_hidden(self) -> bool:
        return self.is_deprecated

    def get_children(self) -> list["Node"]:
        return []


Node = typing.Union[ScalarNode, MappingNode, ReferenceNode]
