import typing
from dataclasses import dataclass

NodePathKey: typing.TypeAlias = str | tuple[str, ...] | int
NodePath: typing.TypeAlias = tuple[NodePathKey, ...]


@dataclass(frozen=True)
class Comment:
    @dataclass(frozen=True)
    class Token:
        value: str
        column: int

    # see some information in ruamel.yaml.comments.Comment and ruamel.yaml.tokens.CommentToken
    values: tuple[None | Token | tuple[Token, ...], ...]


@dataclass(frozen=True)
class _NodeBase:
    path: NodePath
    tag: str
    anchor: None | str
    comment: None | Comment


@dataclass(frozen=True)
class ScalarNode(_NodeBase):
    value: str


@dataclass(frozen=True)
class MappingNode(_NodeBase):
    @dataclass(frozen=True)
    class Item:
        key: "Node"
        value: "Node"
        path: NodePath
        path_key: NodePathKey

    items: typing.OrderedDict[str, Item]

    def __hash__(self) -> int:
        """This is valid if self.items is not edited by anyone"""
        return hash((self.path, self.tag, tuple(self.items.items())))


@dataclass(frozen=True)
class SequenceNode(_NodeBase):
    @dataclass(frozen=True)
    class Item:
        value: "Node"

    values: tuple[Item, ...]


@dataclass(frozen=True)
class ReferenceNode:
    path: NodePath
    referred_node: "Node"  # a reference to an already added node


Node = typing.Union[ScalarNode, MappingNode, SequenceNode, ReferenceNode]
