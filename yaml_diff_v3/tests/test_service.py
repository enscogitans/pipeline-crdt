import pytest

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
    assert merged == my_dedent("""
        A: 1
        B: 2
        C: 3
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


@pytest.mark.skip("Need to fix objects order")
def test_file():
    with open("v0.yml") as f:
        base_text = f.read()
    with open("v1.yml") as f:
        text_1 = f.read()
    with open("v2.yml") as f:
        text_2 = f.read()
    with open("expected.yml") as f:
        expected = f.read()

    service = Service()
    merged = service.merge_with_empty_graph(base_text, text_1, text_2)
    assert merged == expected
