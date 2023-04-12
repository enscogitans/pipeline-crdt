from copy import deepcopy

from yaml_diff_v2.converter import to_yaml, to_graph
from yaml_diff_v2.graph import Timestamp
from yaml_diff_v2.updates.builder import build_updates
from yaml_diff_v2.updates_applier.apply import apply_updates
from yaml_diff_v2.utils import dumps_yaml_node, loads_yaml_node, my_dedent


def check(old_text, new_text):
    old_graph = to_graph(loads_yaml_node(old_text))
    new_graph = to_graph(loads_yaml_node(new_text))
    updates = build_updates(old_graph, new_graph, session_id="test_session", ts=Timestamp(41))

    result_graph = deepcopy(old_graph)
    apply_updates(result_graph, updates)

    result_yaml = dumps_yaml_node(to_yaml(result_graph))
    expected_yaml = dumps_yaml_node(to_yaml(new_graph))
    assert result_yaml == expected_yaml


def test_1():
    a = my_dedent("""
        A: 1
        C: c
        D: dodo
    """)
    b = my_dedent("""
        A: arc
        B:
          X: x
          Y: y
        C: c
    """)
    check(a, b)


def test_2():
    check("1", "2")


def test_3():
    check('"1"', "null")
    check("null", '"1"')
