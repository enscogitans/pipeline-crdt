from textwrap import dedent

from yaml_diff.graph import apply_updates
from yaml_diff.updates_builder import build_yaml_updates
from yaml_diff.utils import loads_yaml, assert_yaml_eq


def check(src, dst, expected, expected_meta=None):
    updates = build_yaml_updates(src, dst, session_id="id_1")
    result = apply_updates(src, updates)
    assert_yaml_eq(result, expected)
    if expected_meta is not None:
        for key in expected_meta:
            assert result.meta[key] == expected_meta[key]


def test_same_dicts():
    src = loads_yaml(dedent("""
        A: 1
        B: 2
    """))
    check(src, src, src)


def test_dict_add():
    src = loads_yaml(dedent("""
        B: 2
        D: 4
    """))
    dst = loads_yaml(dedent("""
        A: 1
        B: 2
        C: 3
        D: 4
    """))
    check(src, dst, dst, expected_meta={
        ("A",): {"session_id": "id_1"},
        ("C",): {"session_id": "id_1"},
    })


def test_dict_del():
    src = loads_yaml(dedent("""
        A: 1
        B: 2
        C: 3
    """))
    dst = loads_yaml(dedent("""
        B: 2
    """))
    check(src, dst, dst, expected_meta={
        ("A",): {"data": 1, "deprecated": True},
        ("C",): {"data": 3, "deprecated": True},
    })


def test_dict_edit():
    src = loads_yaml(dedent("""
        A: 1
        B: 2
        C: 3
    """))
    dst = loads_yaml(dedent("""
        A: 1
        B: b
        C: 4
    """))
    check(src, dst, dst)
