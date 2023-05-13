from collections import OrderedDict

from yaml_diff_v3.utils import loads_yaml_node, get_tag
from yaml_diff_v3.yaml_graph.nodes import ScalarNode, MappingNode, Comment
from yaml_diff_v3.yaml_graph.serialization import deserialize
from yaml_diff_v3.yaml_graph.updates import EditScalarNode, AddMapItem, DeleteMapItem, EditComment, EditMapOrder
from yaml_diff_v3.yaml_graph.updates_builder import build_updates


def get_updates(text_1, text_2):
    graph_1 = deserialize(loads_yaml_node(text_1))
    graph_2 = deserialize(loads_yaml_node(text_2))
    updates = build_updates(graph_1, graph_2)
    return updates


def check(text_1, text_2, expected_updates):
    updates = get_updates(text_1, text_2)
    assert len(updates) == len(set(updates))
    assert set(updates) == set(expected_updates)


def test_edit_scalar():
    check("A: 1", "A: 2", [EditScalarNode(path=("A", 1), tag=get_tag("int"), value="2")])
    check("A: 1", 'A: "1"', [EditScalarNode(path=("A", 1), tag=get_tag("str"), value="1")])
    check("A: 1", "A: a", [EditScalarNode(path=("A", 1), tag=get_tag("str"), value="a")])
    check("[A, session_0]: 1", "[A, session_0]: abba",
          [EditScalarNode(path=(("A", "session_0"), 1), tag=get_tag("str"), value="abba")])

    check("A: {a: 1, b: 2}\nB: [a, b]",
          "A: {a: 11, b: 22}\nB: [aa, bb]",
          [EditScalarNode(path=("A", 1, "a", 1), tag=get_tag("int"), value="11"),
           EditScalarNode(path=("A", 1, "b", 1), tag=get_tag("int"), value="22"),
           EditScalarNode(path=("B", 1, 0), tag=get_tag("str"), value="aa"),
           EditScalarNode(path=("B", 1, 1), tag=get_tag("str"), value="bb")])


def test_add_map_item():
    check("A: 1", "A: 1\nB: 2",
          [AddMapItem(
              map_path=(),
              prev_item_path=("A",),
              next_item_path=None,
              new_item=MappingNode.Item(
                  path=("B",),
                  path_key="B",
                  key=ScalarNode(path=("B", 0), tag=get_tag("str"), value="B", anchor=None, comment=None),
                  value=ScalarNode(path=("B", 1), tag=get_tag("int"), value="2", anchor=None, comment=None),
              ))])

    a = "[1, 2, {B: 2}]"
    b = "[1, 2, {B: 2, A: {X: x}}]"
    new_item = MappingNode.Item(
        path=(2, "A",),
        path_key="A",
        key=ScalarNode(path=(2, "A", 0), tag=get_tag("str"), value="A", anchor=None, comment=None),
        value=MappingNode(path=(2, "A", 1), tag=get_tag("map"), anchor=None, comment=None, items=OrderedDict({
            "X": MappingNode.Item(
                path=(2, "A", 1, "X"),
                path_key="X",
                key=ScalarNode(path=(2, "A", 1, "X", 0), tag=get_tag("str"), value="X", anchor=None, comment=None),
                value=ScalarNode(path=(2, "A", 1, "X", 1), tag=get_tag("str"), value="x", anchor=None, comment=None),
            )
        }))
    )
    check(a, b, [AddMapItem(map_path=(2,), prev_item_path=(2, "B"), next_item_path=None, new_item=new_item)])


def test_add_map_item_order():
    text_1 = """
        C: 3
        E: 5
    """
    text_2 = """
        A: 1
        B: 2
        C: 3
        D: 4
        E: 5
        F: 6
        G: 7
    """
    updates = get_updates(text_1, text_2)

    def check(update: AddMapItem, prev: None | str, next: None | str):
        assert update.map_path == ()
        if prev is None:
            assert update.prev_item_path is None
        else:
            assert update.prev_item_path == (prev,)
        if next is None:
            assert update.next_item_path is None
        else:
            assert update.next_item_path == (next,)

    assert len(updates) == 5
    check(updates[0], None, "C")  # add A
    check(updates[1], "A", "C")  # add B
    check(updates[2], "C", "E")  # add D
    check(updates[3], "E", None)  # add F
    check(updates[4], "F", None)  # add G


def test_del_map_item():
    check("A: 1\nB: {C: {D: d}}", "A: 1", [DeleteMapItem(path=("B", 1))])
    check("A: 1\nB: 2\nC: {D: {E: e, F: f}}",
          "A: 1\nC: {D: {E: e}}",
          [DeleteMapItem(path=("B", 1)), DeleteMapItem(path=("C", 1, "D", 1, "F", 1))])


def test_update_referred_produces_one_update():
    check("A: &a 1\nB: *a", "A: &a 2\nB: *a",
          [EditScalarNode(path=("A", 1), tag=get_tag("int"), value="2")])

    a = """
        A: &a 
          X: x
        B: *a
    """
    b = """
        A: &a
          X: x
          Y: y
        B: *a
    """
    check(a, b, [AddMapItem(
        map_path=("A", 1),
        prev_item_path=("A", 1, "X"),
        next_item_path=None,
        new_item=MappingNode.Item(
            path=("A", 1, "Y"),
            path_key="Y",
            key=ScalarNode(path=("A", 1, "Y", 0), tag=get_tag("str"), value="Y", anchor=None, comment=None),
            value=ScalarNode(path=("A", 1, "Y", 1), tag=get_tag("str"), value="y", anchor=None, comment=None),
    ))])


def test_edit_comment():
    check("A: 1", "A: 1    # comment", [EditComment(path=("A", 1), new_comment=Comment(
        values=(Comment.Token(value="# comment\n", column=8), None)))])


def test_edit_dict_order():
    check("A: 1\nB: 2\nC: 3", "C: 3\nB: 2\nA: 1",
          [EditMapOrder(map_path=(), new_order=(("C",), ("B",), ("A",)))])
    check("""
        A:
          a: 1
          b: 2
        B: 2
    """, """
        B: 2
        A:
          a: 1
          b: 2
    """, [EditMapOrder(map_path=(), new_order=(("B",), ("A",)))])
