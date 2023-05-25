from yaml_diff_v3 import yaml_graph, utils, crdt_graph
from yaml_diff_v3.converter import make_new_crdt_node_from_yaml, make_crdt_updates_from_yaml_updates
from yaml_diff_v3.crdt_graph import Timestamp, SessionId, MappingNode
from yaml_diff_v3.crdt_graph.updates import DeleteMapItem, EditComment, EditScalarNode, EditMapItemSortKey, AddMapItem, \
    AddListItem
from yaml_diff_v3.utils import my_dedent


def make_crdt_updates(old_yaml_text: str, new_yaml_text: str):
    old_yaml_text = my_dedent(old_yaml_text)
    new_yaml_text = my_dedent(new_yaml_text)

    yaml_node = yaml_graph.deserialize(utils.loads_yaml_node(old_yaml_text))
    crdt_node = make_new_crdt_node_from_yaml(yaml_node, Timestamp(0))
    graph = crdt_graph.Graph(root=crdt_node)

    old_yaml_node = yaml_graph.deserialize(utils.loads_yaml_node(old_yaml_text))
    new_yaml_node = yaml_graph.deserialize(utils.loads_yaml_node(new_yaml_text))
    yaml_updates = yaml_graph.build_updates(old_yaml_node, new_yaml_node)
    return graph, make_crdt_updates_from_yaml_updates(yaml_updates, SessionId("session_1"), Timestamp(1), graph)


def test_convert_del_map():
    _, updates = make_crdt_updates("""
        A: &a 1
        B: *a
    """, """
        A: &a 1
    """)

    assert len(updates) == 1 and isinstance(updates[0], DeleteMapItem)


def test_edit_comment_and_value():
    _, updates = make_crdt_updates("A: 1  # Comment 1",
                                   "A: 2  # Comment 2")

    assert len(updates) == 2
    value_update, comment_update = updates
    assert isinstance(value_update, EditScalarNode)
    assert value_update.new_value == "2"

    assert isinstance(comment_update, EditComment)
    assert comment_update.new_comment.values[0].value == "# Comment 2\n"


def test_edit_mapping_order():
    _, updates = make_crdt_updates(
        "A: 1\nB: 2\nC: 3",
        "B: 2\nC: 3\nA: 1",
    )

    assert len(updates) == 1
    assert isinstance(updates[0], EditMapItemSortKey)
    assert "02R" < updates[0].new_sort_key


def test_add_map_items_with_order():
    graph, updates = make_crdt_updates("""
        A: 1
        C: 3
    """, """
        C: 3
        B: 2
        A: 1
        X: 4
    """)

    assert len(updates) == 3

    assert isinstance(updates[0], EditMapItemSortKey)  # either A or C was moved
    is_a_moved = graph.get_node(updates[0].item_id).yaml_path == ("A",)
    if is_a_moved:
        a_sort_key = updates[0].new_sort_key
        c_sort_key = graph.get_path_to_node_mapping()[("C",)].sort_key
    else:
        a_sort_key = graph.get_path_to_node_mapping()[("A",)].sort_key
        c_sort_key = updates[0].new_sort_key

    assert isinstance(updates[1], AddMapItem)
    assert updates[1].new_item.yaml_path == ("B",)
    b_sort_key = updates[1].new_item.sort_key

    assert isinstance(updates[2], AddMapItem)
    assert updates[2].new_item.yaml_path == ("X",)
    x_sort_key = updates[2].new_item.sort_key

    assert c_sort_key < b_sort_key
    assert b_sort_key < a_sort_key
    assert a_sort_key < x_sort_key


def test_add_list_item():
    _, updates = make_crdt_updates("""
        - 1
        - 3
    """, """
        - 1
        - 2
        - 3
    """)

    assert len(updates) == 1
    assert isinstance(updates[0], AddListItem)
    assert isinstance(updates[0].new_item.value, crdt_graph.ScalarNode)
    assert updates[0].new_item.value.value == "2"


def test_add_and_edit_list_item():
    _, updates = make_crdt_updates("""
        A: 1
        B: 
          - 1
          - 3
    """, """
        A: 1
        B: 
          - X: x
          - 2
          - 3
    """)

    assert len(updates) == 2
    upd_0, upd_1 = updates
    if isinstance(upd_0, EditScalarNode):
        upd_0, upd_1 = upd_1, upd_0

    assert isinstance(upd_0, AddListItem)
    assert isinstance(upd_0.new_item.value, MappingNode)

    assert isinstance(upd_1, EditScalarNode)
    assert upd_1.new_value == "2"
