from yaml_diff_v3.service import Service, Timestamp, SessionId
from yaml_diff_v3.utils import my_dedent


def check(base_text, new_text):
    base_text, new_text = map(my_dedent, (base_text, new_text))

    service = Service()

    graph = service.make_initial_crdt_graph(base_text, Timestamp(0))

    session_id = SessionId("session_1")
    ts = Timestamp(1)
    updates = service.build_local_updates(graph, base_text, new_text, session_id, ts)
    service.apply_updates(graph, updates, applied_updates=set())

    result_yaml_text = service.convert_to_yaml(graph)
    assert result_yaml_text == my_dedent(new_text)


def test_service():
    check("""
            A: 1
    """, """
        A: 1
        B:
          X: x
          Y: y
    """)


def test_insert_reference():
    check("""
        A: &a 1
        B: *a
    """, """
        A: &a 1
        B: *a
    """)


def test_delete_reference():
    check("""
        A: &a 1
        B: *a
    """, """
        A: &a 1
    """)


def test_comments():
    check("""
        # Comment
        A: 1            
    """, """
        # Comment 2
        A: 2
    """)

    check("""
        A: 1            
    """, """
        # Add
        # multiple 
          # comments
        A: 2
    """)

    check("""
        # Delete
        # multiple 
          # comments
        A: 2
        # comments
    """, """
        A: 3  # new comment
    """)


def test_add_newlines():
    check("""
        A: 1
        B: 2
    """, """
        A: 1
        
        
        B: 2
    """)
