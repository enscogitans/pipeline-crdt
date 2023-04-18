from yaml_diff_v2.converter import to_yaml, to_graph
from yaml_diff_v2.graph import Timestamp
from yaml_diff_v2.meta_provider import MetaProvider
from yaml_diff_v2.updates.builder import build_updates
from yaml_diff_v2.updates.types import EditScalarNode, DelMapItem, AddMapItem
from yaml_diff_v2.updates_applier.apply import apply_updates
from yaml_diff_v2.utils import *


def dumps_graph(G):
    return dumps_yaml_node(to_yaml(G))


def loads_graph(text, predefined_meta, session_id, ts):
    meta_provider = MetaProvider(predefined_meta, session_id, ts)
    return to_graph(loads_yaml_node(my_dedent(text)), meta_provider), meta_provider.meta


def update_meta(graph, updates, ts):
    for update in updates:
        if isinstance(update, EditScalarNode):
            graph.get_item_by_id(update.item_id).meta.last_edit_ts = ts
        elif isinstance(update, AddMapItem):
            pass  # new item already has valid meta
        elif isinstance(update, DelMapItem):
            graph.get_item_by_id(update.item_id).meta.is_deprecated = True
        else:
            raise NotImplementedError(f"Unexpected update {type(update)}")


def check(base_text, text_1, text_2, expected_text):
    expected_text = my_dedent(expected_text)

    base_graph, base_meta = loads_graph(base_text, {}, "session_0", Timestamp(0))
    graph_1, _ = loads_graph(text_1, base_meta, "session_1", Timestamp(10))
    graph_2, _ = loads_graph(text_2, base_meta, "session_2", Timestamp(20))

    updates_1 = build_updates(base_graph, graph_1, ts=Timestamp(10))
    update_meta(graph_1, updates_1, Timestamp(10))

    updates_2 = build_updates(base_graph, graph_2, ts=Timestamp(20))
    update_meta(graph_2, updates_2, Timestamp(20))

    result_1 = deepcopy(graph_1)
    apply_updates(result_1, updates_2)
    assert dumps_graph(result_1) == expected_text

    result_2 = deepcopy(graph_2)
    apply_updates(result_2, updates_1)
    assert dumps_graph(result_2) == expected_text


def test_add_same_key():
    a = "B: b"
    b = "A: 1\nB: b"
    c = "A: a\nB: b"
    expected = """
        [A, session_1]: 1
        [A, session_2]: a
        B: b
    """
    check(a, b, c, expected)


def test_apply_latest_update():
    a = "A: 1"
    b = "A: 2"
    c = "A: 3"
    expected = "A: 3"
    check(a, b, c, expected)
