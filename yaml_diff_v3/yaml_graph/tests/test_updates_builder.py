from collections import OrderedDict

from yaml_diff_v3.utils import loads_yaml_node, get_tag
from yaml_diff_v3.yaml_graph.nodes import ScalarNode, MappingNode
from yaml_diff_v3.yaml_graph.serialization import deserialize
from yaml_diff_v3.yaml_graph.updates import EditScalarNode, AddMapItem, DeleteMapItem
from yaml_diff_v3.yaml_graph.updates_builder import build_updates


def check(text_1, text_2, expected_updates):
    graph_1 = deserialize(loads_yaml_node(text_1))
    graph_2 = deserialize(loads_yaml_node(text_2))
    updates = build_updates(graph_1, graph_2)
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
          [AddMapItem(map_path=(), new_item=MappingNode.Item(
              path_key="B",
              key=ScalarNode(path=("B", 0), tag=get_tag("str"), value="B", anchor=None),
              value=ScalarNode(path=("B", 1), tag=get_tag("int"), value="2", anchor=None),
          ))])

    a = "[1, 2, {B: 2}]"
    b = "[1, 2, {B: 2, A: {X: x}}]"
    new_item = MappingNode.Item(
        path_key="A",
        key=ScalarNode(path=(2, "A", 0), tag=get_tag("str"), value="A", anchor=None),
        value=MappingNode(path=(2, "A", 1), tag=get_tag("map"), anchor=None, items=OrderedDict({
            "X": MappingNode.Item(
                path_key="X",
                key=ScalarNode(path=(2, "A", 1, "X", 0), tag=get_tag("str"), value="X", anchor=None),
                value=ScalarNode(path=(2, "A", 1, "X", 1), tag=get_tag("str"), value="x", anchor=None),
            )
        }))
    )
    check(a, b, [AddMapItem(map_path=(2,), new_item=new_item)])


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
    check(a, b, [AddMapItem(map_path=("A", 1), new_item=MappingNode.Item(
        path_key="Y",
        key=ScalarNode(path=("A", 1, "Y", 0), tag=get_tag("str"), value="Y", anchor=None),
        value=ScalarNode(path=("A", 1, "Y", 1), tag=get_tag("str"), value="y", anchor=None),
    ))])
