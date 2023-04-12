from copy import deepcopy
from typing import Union

from yaml_diff_v2.graph import MapItem, ItemId, Timestamp


class EditScalarNode:
    def __init__(self, item_id: ItemId, new_tag: str, new_value: str, ts: Timestamp):
        self.item_id = item_id
        self.new_tag = new_tag
        self.new_value = new_value
        self.ts = ts


class AddMapItem:
    def __init__(self, container_item_id: ItemId, node: MapItem):
        self.container_item_id = container_item_id  # Container where to insert value
        self.new_node = deepcopy(node)


class DelMapItem:
    def __init__(self, item_id: ItemId):
        self.item_id = item_id


Update = Union[EditScalarNode, AddMapItem, DelMapItem]
