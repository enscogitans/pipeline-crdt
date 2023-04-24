from yaml_diff_v3 import yaml_graph, utils, crdt_graph
from yaml_diff_v3.converter import make_new_crdt_node_from_yaml, make_crdt_updates_from_yaml_updates
from yaml_diff_v3.crdt_graph import Timestamp, SessionId
from yaml_diff_v3.crdt_graph.updates import DeleteMapItem


def make_crdt_updates(old_yaml_text: str, new_yaml_text: str):
    yaml_node = yaml_graph.deserialize(utils.loads_yaml_node(old_yaml_text))
    crdt_node = make_new_crdt_node_from_yaml(yaml_node, Timestamp(0))
    graph = crdt_graph.Graph(root=crdt_node)

    old_yaml_node = yaml_graph.deserialize(utils.loads_yaml_node(old_yaml_text))
    new_yaml_node = yaml_graph.deserialize(utils.loads_yaml_node(new_yaml_text))
    yaml_updates = yaml_graph.build_updates(old_yaml_node, new_yaml_node)
    return make_crdt_updates_from_yaml_updates(yaml_updates, SessionId("session_1"), Timestamp(1), graph)


def test_convert_del_map():
    updates = make_crdt_updates("""
        A: &a 1
        B: *a
    """, """
        A: &a 1
    """)

    assert len(updates) == 1 and isinstance(updates[0], DeleteMapItem)
