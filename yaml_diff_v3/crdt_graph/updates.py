from dataclasses import dataclass
from typing import NewType

from yaml_diff_v3.crdt_graph.nodes import NodeId, MappingNode, Timestamp, Comment, SequenceNode

SessionId = NewType("SessionId", str)
UpdateId = NewType("UpdateId", str)


@dataclass
class Update:
    session_id: SessionId
    timestamp: Timestamp
    update_id: UpdateId


@dataclass
class EditScalarNode(Update):
    node_id: NodeId
    new_yaml_tag: str
    new_value: str


@dataclass
class EditComment(Update):
    node_id: NodeId
    new_comment: Comment


@dataclass
class AddMapItem(Update):
    mapping_node_id: NodeId
    new_item: MappingNode.Item


@dataclass
class DeleteMapItem(Update):
    item_value_id: NodeId  # Id of deleted item.value


@dataclass
class EditMapItemSortKey(Update):
    item_id: NodeId
    new_sort_key: str


@dataclass
class AddListItem(Update):
    list_node_id: NodeId
    new_item: SequenceNode.Item


@dataclass
class DeleteListItem(Update):
    item_id: NodeId


@dataclass
class EditListItemSortKey(Update):
    item_id: NodeId
    new_sort_key: str
