from textwrap import dedent

from yaml_diff.graph import apply_updates
from yaml_diff.updates_builder import build_yaml_updates
from yaml_diff.utils import loads_yaml, assert_yaml_eq


def check(src, dst, expected):
    updates = build_yaml_updates(src, dst)
    result = apply_updates(src, updates)
    assert_yaml_eq(result, expected)


def test_same_lists():
    src = loads_yaml(dedent("""
        - A
        - B
    """))
    check(src, src, src)


def test_list_add():
    src = loads_yaml(dedent("""
        - B
        - D
    """))
    dst = loads_yaml(dedent("""
        - A
        - B
        - C
        - D
    """))
    check(src, dst, dst)


def test_list_del():
    src = loads_yaml(dedent("""
        - A
        - B
        - C
    """))
    dst = loads_yaml(dedent("""
        - B
    """))
    exp = loads_yaml(dedent("""
        - !<TaggedData>
          data: A
          deprecated: true
        - B
        - !<TaggedData>
          data: C
          deprecated: true
    """))
    check(src, dst, exp)


def test_list_edit():
    src = loads_yaml(dedent("""
        - A
        - B
        - C
    """))
    dst = loads_yaml(dedent("""
        - A
        - b
        - 3
    """))
    check(src, dst, dst)
