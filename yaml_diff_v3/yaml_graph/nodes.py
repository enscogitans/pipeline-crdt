import typing
from dataclasses import dataclass
from typing import Union

NodePathKey: typing.TypeAlias = str | tuple[str, ...] | int
NodePath: typing.TypeAlias = tuple[NodePathKey, ...]


@dataclass(frozen=True)
class ScalarNode:
    path: NodePath
    tag: str
    value: str


@dataclass(frozen=True)
class MappingNode:
    @dataclass(frozen=True)
    class Item:
        key: "Node"
        value: "Node"
        path_key: NodePathKey

    path: NodePath
    tag: str
    items: typing.OrderedDict[str, Item]

    def __hash__(self) -> int:
        """This is valid if self.items is not edited by anyone"""
        return hash((self.path, self.tag, tuple(self.items.items())))


@dataclass(frozen=True)
class SequenceNode:
    path: NodePath
    tag: str
    values: tuple["Node", ...]


Node = Union[ScalarNode, MappingNode, SequenceNode]
