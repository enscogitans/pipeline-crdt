import pytest

from yaml_diff_v2.converter import to_yaml, to_graph
from yaml_diff_v2.graph import MapNode
from yaml_diff_v2.utils import *


def check(src_text: str, expected=None):
    src_text = my_dedent(src_text)
    graph = to_graph(loads_yaml_node(src_text))
    dst_text = dumps_yaml_node(to_yaml(graph))
    if expected is None:
        assert src_text == dst_text.rstrip()
    else:
        expected = my_dedent(expected)
        assert expected == dst_text.rstrip()


def test_simple():
    check("""
        A: a
        B: b    
    """)


def test_tag():
    check("""
        A: !Tag
          X: x
          Y: 1441    
    """)


def test_composite_key_read():
    graph = to_graph(loads_yaml_node("""
        [A, session_0]: 100
    """))
    assert isinstance(graph.root, MapNode)
    assert ("A", "session_0") in graph.root.items
    map_item = graph.root.items[("A", "session_0")]
    assert map_item.key.scalar.value == "A"
    assert map_item.key.unique_id == "session_0"


@pytest.mark.skip("Enable when meta reader is done")
def test_composite_key():
    check("""
        [A, session_0]: 100
    """, expected="""
        A: 100
    """)
    check("""
        [A, session_0]: 100
        [A, session_1]: 200
    """)


@pytest.mark.skip("Comments are not implemented yet")
def test_comment():
    check("""
        A:  # comment for A
          X: x
          Y: 1441    
    """)
