import re
from copy import deepcopy
from pathlib import Path

from yaml_diff_v3.crdt_graph import Timestamp, SessionId
from yaml_diff_v3.service import Service
from yaml_diff_v3.utils import my_dedent


def test_two_map_inserts():
    old_yaml_text = """
        A: 1
    """
    yaml_text_1 = """
        A: 1
        B: 2
    """
    yaml_text_2 = """
        A: 1
        C: 3
    """
    service = Service()
    merged = service.merge_with_empty_graph(old_yaml_text, yaml_text_1, yaml_text_2)
    assert merged in ("A: 1\nB: 2\nC: 3\n", "A: 1\nC: 3\nB: 2\n")


def test_two_list_inserts():
    old_yaml_text = """
        - 1
        - 2
    """
    yaml_text_1 = """
        - 1
        - - x
          - y
        - 2
    """
    yaml_text_2 = """
        - 1
        - 2
        - A: a
          B: b
    """
    service = Service()
    merged = service.merge_with_empty_graph(old_yaml_text, yaml_text_1, yaml_text_2)
    assert merged == my_dedent("""
        - 1
        - - x
          - y
        - 2
        - A: a
          B: b
    """)


def test_two_list_inserts_and_permutations():
    old_yaml_text = """
        - 1
        - - x
          - y
        - 2
        - A: a
          B: b
    """
    yaml_text_1 = """
        - 1
        - B: b
          A: a
        - 2
        - - y
          - x
        - 3
    """
    yaml_text_2 = """
        - 0
        - 1
        - - x
          - y
        - 2
        - A: a
          B: b
    """
    service = Service()
    merged = service.merge_with_empty_graph(old_yaml_text, yaml_text_1, yaml_text_2)
    assert merged == my_dedent("""
        - 0
        - 1
        - B: b
          A: a
        - 2
        - - y
          - x
        - 3
    """)


def test_two_comment_edits():
    old_yaml_text = my_dedent("""
        A: 1
        
        B: 2
    """)
    yaml_text_1 = my_dedent("""
        # Comment for A
        A: 1
        
        B: 2
    """)
    yaml_text_2 = my_dedent("""
        # More recent comment for A
        A: 1
        
        B: 2  # One more comment
    """)
    service = Service()
    merged = service.merge_with_empty_graph(old_yaml_text, yaml_text_1, yaml_text_2)
    assert merged == my_dedent("""
        # More recent comment for A
        A: 1
        
        B: 2  # One more comment
    """)


def test_3_stages():
    base_yaml_text = my_dedent("""
        - 1
        - - x
          - y
        - 2
        - A: a
          B: b
    """)
    service = Service()
    graph_1 = service.make_initial_crdt_graph(base_yaml_text, Timestamp(0))
    graph_2 = deepcopy(graph_1)

    yaml_text_1 = my_dedent("""
        - 1
        - B: b
          A: a
        - 2
        - - y
          - x
        - 3
    """)
    updates_1 = service.build_local_updates(graph_1, base_yaml_text, yaml_text_1, SessionId("session_1"), Timestamp(1))
    service.apply_updates(graph_1, updates_1, set())

    yaml_text_2 = my_dedent("""
        - 0
        - 1
        - - x
          - y
        - 2
        - A: a
          B: b
    """)
    updates_2 = service.build_local_updates(graph_2, base_yaml_text, yaml_text_2, SessionId("session_2"), Timestamp(2))
    service.apply_updates(graph_2, updates_2, set())
    service.apply_updates(graph_2, updates_1, set())
    base_yaml_text = service.convert_to_yaml(graph_2)
    assert base_yaml_text == my_dedent("""
        - 0
        - 1
        - B: b
          A: a
        - 2
        - - y
          - x
        - 3
    """)
    yaml_text_3 = my_dedent("""
        - B: b
          A: a
        - - y
          - x
        - echo 123
    """)
    updates_3 = service.build_local_updates(graph_2, base_yaml_text, yaml_text_3, SessionId("session_3"), Timestamp(3))
    service.apply_updates(graph_2, updates_3, set())

    service.apply_updates(graph_1, updates_2, set())
    service.apply_updates(graph_1, updates_3, set())

    result_1 = service.convert_to_yaml(graph_1)
    result_2 = service.convert_to_yaml(graph_2)
    assert result_2 == yaml_text_3
    assert result_1 == result_2


def test_file():
    test_dir = Path(__file__).parent / "data" / "case_1"
    with open(test_dir / "v0.yml") as f:
        base_text = f.read()
    with open(test_dir / "v1.yml") as f:
        text_1 = f.read()
    with open(test_dir / "v2.yml") as f:
        text_2 = f.read()
    with open(test_dir / "expected.yml") as f:
        expected = f.read()

    service = Service()
    merged = service.merge_with_empty_graph(base_text, text_1, text_2)
    assert merged == expected


def test_file_2():
    test_dir = Path(__file__).parent / "data" / "case_2"
    with open(test_dir / "v0.yml") as f:
        base_text = f.read()
    with open(test_dir / "v1.yml") as f:
        text_1 = f.read()
    with open(test_dir / "v2.yml") as f:
        text_2 = f.read()
    with open(test_dir / "expected_regex.yml") as f:
        expected_regex = f.read()
    expected_regex = re.escape(expected_regex)
    expected_regex = expected_regex.replace("RE_UUID", r"[\w-]+")

    service = Service()
    merged = service.merge_with_empty_graph(base_text, text_1, text_2)
    assert re.fullmatch(expected_regex, merged)
    # assert merged == expected
