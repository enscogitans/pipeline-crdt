import pytest

from yaml_diff_v3.utils import my_dedent, loads_yaml_node, dumps_yaml_node, get_tag
from yaml_diff_v3.yaml_graph import serialization
from yaml_diff_v3.yaml_graph.nodes import MappingNode, ScalarNode


def check(text: str):
    text = my_dedent(text)
    serialized = loads_yaml_node(text)

    root = serialization.deserialize(serialized)
    serialized_2 = serialization.serialize(root)

    output_text = dumps_yaml_node(serialized_2)
    assert output_text == text


def test_list():
    check("""
        - 1
        - 2
    """)
    check("""
        - 1
        - - 2
          - 3
        - abc
    """)


def test_dict():
    check("""
        A: a
        B: b
    """)
    check("""
        A: a
        B:
          X: x
          Y:
          - 1
          - 2
    """)


def test_dict_2():
    text = "A: {a: 1}"
    root = serialization.deserialize(loads_yaml_node(text))
    assert isinstance(root, MappingNode)
    assert root.path == ()

    [(key_elem, item)] = root.items.items()
    assert key_elem == "A"
    assert item.key == ScalarNode(path=("A", 0), tag=get_tag("str"), value="A", anchor=None, comment=None)
    assert isinstance(item.value, MappingNode)
    assert item.value.path == ("A", 1)

    [(inner_key_elem, inner_item)] = item.value.items.items()
    assert inner_key_elem == "a"
    assert inner_item.key == ScalarNode(path=("A", 1, "a", 0), tag=get_tag("str"), value="a", anchor=None, comment=None)
    assert inner_item.value == ScalarNode(path=("A", 1, "a", 1), tag=get_tag("int"), value="1",
                                          anchor=None, comment=None)


def test_tag():
    check("""
        A: !Tag
          X: x
          Y: 1441    
    """)


def test_composite_key():
    check("""
        [A, session_0]: 100
        [A, session_1]: 200
    """)


def test_key_dict_error():
    serialized = loads_yaml_node("{1: 2}: 100")
    with pytest.raises(TypeError, match=r"Only a scalar or a pair of scalars can be a key"):
        serialization.deserialize(serialized)


def test_comment():
    check("""
        # Comment for A
        A:
          X: x
          Y: 1441    
    """)
    check("""
        A: # Comment after A
          X: x
          Y: 1441
    """)
    check("""
          # Comments
        A:    # Are
         # Everywhere
          X: x
          Y: 1441  # Hello
        # Wow
    """)


def test_newlines():
    # In ruamel newlines are implemented using comments mechanism
    check("""
        A:

          X: x


          Y: 1441    
    """)


def test_merge():
    check("""
        A: &a
        - 1
        - 2
        B: *a
    """)
    check("""
        A: &a
          X: x
          Y: y
        B: *a
        <<: *a
    """)
