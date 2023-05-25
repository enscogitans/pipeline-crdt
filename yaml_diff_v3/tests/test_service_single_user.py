import pytest

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


def test_dict_order():
    check("""
        A: 1
        B: 2
        C: 3
    """, """
        C: 3
        B: 2
        A: 1
    """)


def test_insert_order():
    check("""
        A:
          b: 2
        B: 2
    """, """
        A:
          a: 1
          b: 2
        B: 2
    """)
    check("""
        A:
          a: 1
        B: 2
    """, """
        A:
          a: 1
          b: 2
        B: 2
    """)


def test_list_order():
    check("""
        - 1
        - 2
        - 3
    """, """
        - 3
        - 2
        - 1
    """)


def test_list_order_and_edit():
    check("""
        - - 1
          - 2
        - - a
          - b
    """, """
        - - b
          - a
        - - 22
          - 11
    """)


def test_add_list_item():
    check("""
        - 1
    """, """
        - 1
        - 2
    """)


def test_delete_list_item():
    check("""
        - 1
        - 2
        - 3
    """, """
        - 1

        - 3
    """)


@pytest.mark.skip("Fix dict keys")
def test_delete_dict_item_inside_list():
    check("""
        - 1
        -
          A: a
          B: b
          C: c
        - 3
    """, """
        - 
          C: c
          B: b
        - 3
        - 1
    """)
