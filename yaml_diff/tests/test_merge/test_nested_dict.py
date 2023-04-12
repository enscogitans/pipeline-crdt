from textwrap import dedent

from yaml_diff.graph import merge_yaml
from yaml_diff.utils import loads_yaml, assert_yaml_eq


def check(base, a, b, expected, meta=None):
    merged = merge_yaml(base, a, "id_1", 1, b, "id_2", 2)
    assert_yaml_eq(expected, merged)
    if meta is not None:
        for key in meta:
            assert merged.meta[key] == meta[key]
    merged_2 = merge_yaml(base, b, "id_2", 2, a, "id_1", 1)
    assert_yaml_eq(expected, merged_2)


def test_dict_add_same_key():
    base = loads_yaml(dedent("""
        data:
          A: 1
          C: 3
    """))
    a = loads_yaml(dedent("""
        data:
          A: 1
          B: 2
          C: 3
    """))
    b = loads_yaml(dedent("""
        data:
          A: 1
          B: b
          C: 3
    """))
    expected = loads_yaml(dedent("""
        data:
          A: 1
          B: !<MultiMap>
            id_1: 2
            id_2: b
          C: 3
    """))
    check(base, a, b, expected, meta={
        ("data", "B", "id_1"): dict(session_id="id_1"),
        ("data", "B", "id_2"): dict(session_id="id_2"),
    })


def test_dict_add_different_key():
    base = loads_yaml(dedent("""
        data:
            A: 1
            B: !<MultiMap>
              id_10:
                X: 0
              id_20: b
    """))
    a = loads_yaml(dedent("""
        data:
            A: 1
            B: !<MultiMap>
              id_10:
                X: 0
              id_20: b
            C: 3
    """))
    b = loads_yaml(dedent("""
        data:
            A: 1
            B: !<MultiMap>
              id_10:
                X: 0
                Y: -1
              id_20: b
    """))

    expected = loads_yaml(dedent("""
        data:
            A: 1
            B: !<MultiMap>
              id_10:
                X: 0
                Y: -1
              id_20: b
            C: 3  
    """))
    check(base, a, b, expected, meta={
        ("data", "B", "id_10", "Y"): dict(session_id="id_2"),
        ("data", "C",): dict(session_id="id_1"),
    })


def test_dict_edit_different_key():
    base = loads_yaml(dedent("""
        data:
            A: 1
            B: 2
            C: 3
    """))
    a = loads_yaml(dedent("""
        data:
            A: 1
            B: b
            C: 3
    """))
    b = loads_yaml(dedent("""
        data:
            A: 1
            B: 2
            C: C
    """))

    expected = loads_yaml(dedent("""
        data:
            A: 1
            B: b
            C: C
    """))
    check(base, a, b, expected, meta={
        ("data", "B"): dict(last_edit_ts=1),
        ("data", "C"): dict(last_edit_ts=2),
    })


def test_edit_same_key():
    base = loads_yaml(dedent("""
        data:
            A: 1
            B: 2
            C: 3
    """))
    a = loads_yaml(dedent("""
        data:
            A: 1
            B: b
            C: 3
    """))
    b = loads_yaml(dedent("""
        data:
            A: 1
            B: B
            C: 3
    """))

    # The last update wins
    expected = loads_yaml(dedent("""
        data:
            A: 1
            B: B
            C: 3
    """))
    check(base, a, b, expected)
