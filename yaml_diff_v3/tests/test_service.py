from yaml_diff_v3.service import Service, Timestamp, SessionId
from yaml_diff_v3.utils import my_dedent


def test_service():
    service = Service()

    old_yaml_text = "A: 1"
    graph = service.make_initial_crdt_graph(old_yaml_text, Timestamp(0))

    new_yaml_text = """
        A: 1
        B:
          X: x
          Y: y
    """
    session_id = SessionId("session_1")
    ts = Timestamp(1)
    updates = service.build_local_updates(graph, old_yaml_text, new_yaml_text, session_id, ts)
    service.apply_updates(graph, updates, applied_updates=set())

    result_yaml_text = service.convert_to_yaml(graph)
    assert result_yaml_text == my_dedent(new_yaml_text)
