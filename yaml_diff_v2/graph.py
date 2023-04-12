import abc
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import NewType

ItemId = NewType("ItemId", tuple[str | tuple[str, str], ...])  # path from graph root to node
Timestamp = NewType("Timestamp", int)


@dataclass
class NodeMeta:
    creation_key: str
    last_edit_ts: Timestamp
    is_deprecated: bool
    is_all_children_hidden: bool

    @property
    def is_hidden(self) -> bool:
        return self.is_deprecated and self.is_all_children_hidden


class Item(abc.ABC):  # A node of a Graph that does not correspond to any node in yaml
    def __init__(self, item_id: ItemId):
        self.item_id: ItemId = item_id


class Node(Item, abc.ABC):
    def __init__(self, item_id: ItemId, yaml_tag: str, meta: NodeMeta):
        super(Node, self).__init__(item_id)
        self.yaml_tag: str = yaml_tag
        self.meta = meta

    @abc.abstractmethod
    def get_children(self) -> list["Node"]: ...

    @property
    def is_hidden(self) -> bool:
        return self.meta.is_hidden


class ScalarNode(Node):
    def __init__(self, item_id: ItemId, yaml_tag, value: str, meta: NodeMeta):
        super().__init__(item_id, yaml_tag, meta)
        self.value: str = value
        self.meta.is_all_children_hidden = True  # There are no children

    def get_children(self) -> list["Node"]:
        return []


class MapKey:
    def __init__(self, scalar: ScalarNode, unique_id: str):
        self.scalar = scalar
        self.unique_id = unique_id

    def as_tuple(self) -> tuple[str, str]:
        return self.scalar.value, self.unique_id


class MapItem(Item):  # Just a container for a pair of key and value
    def __init__(self, item_id: ItemId, key: MapKey, value: Node):
        super().__init__(item_id)
        self.key = key
        self.value = value


class MapNode(Node):
    def __init__(self, item_id: ItemId, yaml_tag, items: list[MapItem], meta: NodeMeta):
        super().__init__(item_id, yaml_tag, meta)
        self.items: dict[tuple[str, str], MapItem] = OrderedDict((item.key.as_tuple(), item) for item in items)

    def get_children(self) -> list["Node"]:
        return [map_item.value for map_item in self.items.values()]


class Graph:
    def __init__(self, root: Node):
        self.root = root

    def get_item_by_id(self, item_id: ItemId) -> Item:
        def dfs(node: Node):
            if node.item_id == item_id:
                return node
            for child in node.get_children():
                res = dfs(child)
                if res is not None:
                    return res
            return None

        res = dfs(self.root)
        assert res is not None
        return res

        # for path_elem in item_id:
        #     assert not isinstance(node, ScalarNode)  # It is always expected to be a final node
        #
        #     if isinstance(node, MapItem):
        #         if path_elem == "key":
        #             node = node.key
        #         else:
        #             assert path_elem == "value"
        #             node = node.value
        #
        #     elif isinstance(node, MapNode):
        #         node = node.items[path_elem]
        #
        #     else:
        #         raise NotImplementedError(f"Unexpected node type {node}")
        #
        # return node

    def edit_scalar_node(self, item_id: ItemId, new_value: str, new_tag: str, ts: Timestamp) -> None:
        scalar_node = self.get_item_by_id(item_id)
        assert isinstance(scalar_node, ScalarNode)
        if scalar_node.meta.last_edit_ts > ts:
            return
        scalar_node.value = new_value
        scalar_node.yaml_tag = new_tag
        scalar_node.meta.last_edit_ts = ts

    def add_map_item(self, map_id: ItemId, map_item: MapItem) -> None:
        map_node = self.get_item_by_id(map_id)
        assert isinstance(map_node, MapNode)
        key = map_item.key.as_tuple()
        assert key not in map_node.items, "Duplicate tuple key"
        map_node.items[key] = deepcopy(map_item)

    def _update_is_all_children_hidden(self, node: Node) -> None:
        for child in node.get_children():
            self._update_is_all_children_hidden(child)
        node.meta.is_all_children_hidden = all(child.is_hidden for child in node.get_children())  # True if list empty

    def _set_deprecated(self, node: Node) -> None:
        if node.meta.is_deprecated:
            return
        node.meta.is_deprecated = True
        for child in node.get_children():
            self._set_deprecated(child)

    def del_map_item(self, map_id: ItemId) -> None:
        map_node = self.get_item_by_id(map_id)
        assert isinstance(map_node, MapItem)
        self._set_deprecated(map_node.value)

    def _iter_nodes(self):
        def dfs(node: Node):
            yield node
            for child in node.get_children():
                yield from dfs(child)

        yield from dfs(self.root)

    def make_meta(self) -> dict[ItemId, NodeMeta]:
        return {node.item_id: node for node in self._iter_nodes()}
