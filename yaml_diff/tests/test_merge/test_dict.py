from textwrap import dedent

from yaml_diff.graph import merge_yaml
from yaml_diff.utils import loads_yaml, assert_yaml_eq


def check(base_text, a_text, b_text, expected_text, meta=None):
    base = loads_yaml(dedent(base_text))
    a = loads_yaml(dedent(a_text))
    b = loads_yaml(dedent(b_text))
    expected = loads_yaml(dedent(expected_text))
    merged = merge_yaml(base, a, "id_1", 1, b, "id_2", 2)
    assert_yaml_eq(expected, merged)
    if meta is not None:
        for key in meta:
            assert merged.meta[key] == meta[key]
    base = loads_yaml(dedent(base_text))  # base was modified
    merged_2 = merge_yaml(base, b, "id_2", 2, a, "id_1", 1)
    assert_yaml_eq(expected, merged_2)


def test_dict_add_same_key():
    base = (("""
        A: 1
        C: 3
    """))
    a = (("""
        A: 1
        B: 2
        C: 3
    """))
    b = (("""
        A: 1
        B: b
        C: 3
    """))
    expected = (("""
        A: 1
        B: !<MultiMap>
          id_1: 2
          id_2: b
        C: 3
    """))
    check(base, a, b, expected, meta={
        ("B", "id_1"): dict(session_id="id_1"),
        ("B", "id_2"): dict(session_id="id_2"),
    })


def test_dict_add_different_key():
    base = (("""
        A: 1
        C: 3
    """))
    a = (("""
        A: 1
        B: 2
        C: 3
    """))
    b = (("""
        A: 1
        C: 3
        D: 4
    """))

    expected = (("""
        A: 1
        B: 2
        C: 3
        D: 4
    """))
    check(base, a, b, expected, meta={
        ("B",): dict(session_id="id_1"),
        ("D",): dict(session_id="id_2"),
    })


def test_dict_edit_different_key():
    base = (("""
        A: 1
        B: 2
        C: 3
    """))
    a = (("""
        A: 1
        B: b
        C: 3
    """))
    b = (("""
        A: 1
        B: 2
        C: C
    """))

    expected = (("""
        A: 1
        B: b
        C: C
    """))
    check(base, a, b, expected)


def test_edit_same_key():
    base = (("""
        A: 1
        B: 2
        C: 3
    """))
    a = (("""
        A: 1
        B: b
        C: 3
    """))
    b = (("""
        A: 1
        B: B
        C: 3
    """))

    # The last update wins
    expected = (("""
        A: 1
        B: B
        C: 3
    """))
    check(base, a, b, expected)
