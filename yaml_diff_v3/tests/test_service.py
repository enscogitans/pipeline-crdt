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
