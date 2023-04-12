from copy import deepcopy

from yaml_diff_v2.graph import Timestamp, ItemId, NodeMeta


class MetaProvider:
    def __init__(self, predefined_meta: dict[ItemId, NodeMeta], session_id: str, ts: Timestamp):
        self.meta = deepcopy(predefined_meta)
        self.session_id = session_id
        self.ts = ts

    def _make_meta(self) -> NodeMeta:
        return NodeMeta(
            creation_key=self.session_id,
            last_edit_ts=self.ts,
            is_deprecated=False,
            is_all_children_hidden=False,
        )

    def get_meta(self, key: ItemId) -> NodeMeta:
        if key in self.meta:
            return self.meta[key]
        self.meta[key] = self._make_meta()
        return self.meta[key]

    def find_full_key(self, partial_key: ItemId) -> ItemId:
        matching = []
        for key, value in self.meta.items():
            prefix = key[:len(partial_key)]
            if prefix and isinstance(prefix[-1], tuple) and not value.is_hidden and \
                    prefix[:-1] == partial_key[:-1] and prefix[-1][0] == partial_key[-1]:
                matching.append(prefix)
        if len(set(matching)) > 1:
            raise Exception("Can use partial key only if complex key is absent")
        if matching:
            return matching[0]
        return partial_key[:-1] + ((partial_key[-1], self.session_id),)
