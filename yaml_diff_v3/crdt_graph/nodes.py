import abc
from dataclasses import dataclass
from typing import NewType

from yaml_diff_v3 import yaml_graph

NodeId = NewType("NodeId", str)
Timestamp = NewType("Timestamp", int)


@dataclass
class Node(abc.ABC):
    id: NodeId  # globally unique
    yaml_tag: str
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
class ScalarNode(Node):
    value: str

    def get_children(self) -> list[Node]:
        return []


@dataclass
class MappingNode(Node):
    @dataclass
    class Item:
        key: ScalarNode
        value: Node  # value is the main, key is its satellite. All operations applied to an Item modify value, not key

    items: list[Item]

    def get_children(self) -> list[Node]:
        return [item.value for item in self.items]
