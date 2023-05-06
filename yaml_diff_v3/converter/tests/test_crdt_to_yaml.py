from yaml_diff_v3 import converter
from yaml_diff_v3 import yaml_graph
from yaml_diff_v3.crdt_graph import Timestamp, Graph
from yaml_diff_v3.utils import loads_yaml_node, dumps_yaml_node, my_dedent
from yaml_diff_v3.yaml_graph import serialization


def check(yaml_text):
    yaml_text = my_dedent(yaml_text)
    yaml_node = serialization.deserialize(loads_yaml_node(yaml_text))

    crdt_node = converter.make_new_crdt_node_from_yaml(yaml_node, Timestamp(0))

    yaml_node_2 = converter.crdt_graph_to_yaml_node(Graph(crdt_node))
    result_text = dumps_yaml_node(serialization.serialize(yaml_node_2))

    assert result_text == yaml_text


def test_same_node():
    yaml_text = "A: &a 1\nB: *a"
    yaml_node = serialization.deserialize(loads_yaml_node(yaml_text))
    assert isinstance(yaml_node.items["B"].value, yaml_graph.ReferenceNode)
    # This is one object (because of the & and *)
    assert yaml_node.items["A"].value is yaml_node.items["B"].value.referred_node

    crdt_node = converter.make_new_crdt_node_from_yaml(yaml_node, Timestamp(0))
    assert crdt_node.items[0].value.id == crdt_node.items[1].value.referred_id

    yaml_node_2 = converter.crdt_graph_to_yaml_node(Graph(crdt_node))
    assert isinstance(yaml_node_2.items["B"].value, yaml_graph.ReferenceNode)
    assert yaml_node_2.items["A"].value is yaml_node_2.items["B"].value.referred_node


def test_reference():
    check("""
        A: &a 1
        B: *a
    """)


def test_comments():
    check("""
        # Comment
        A: 1
    """)
    check("""
           # Shifted Comment
        A: 1
    """)
    check("""
         # Some
        A: 1     # mess
           # with comments 
    """)
