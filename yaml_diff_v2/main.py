import io

from deepdiff import DeepDiff

from yaml_diff_v2.converter import to_yaml, to_graph
from yaml_diff_v2.graph import Timestamp
from yaml_diff_v2.updates.builder import build_updates
from yaml_diff_v2.updates_applier.apply import apply_updates
from yaml_diff_v2.utils import *


def dumps_graph(G):
    return dumps_yaml_node(to_yaml(G))


def main():
    a = dedent("""
        A: 1
        C: c
    """)
    b = dedent("""
        A: 1
        B: 2
        C: c
    """)
    c = dedent("""
        A: a
        B: b
        C: c
    """)

    G1 = to_graph(loads_yaml_node(a))
    G2 = to_graph(loads_yaml_node(b))
    updates = build_updates(G1, G2, "session_1", Timestamp(19))

    print(dumps_graph(G1))
    apply_updates(G1, updates)
    print(dumps_graph(G1))
    print(dumps_graph(G2))


if __name__ == "__main__":
    # main()


    print(DeepDiff({('a', '1'): 2}, {('a', '1'): 3, 'a': 4}, verbose_level=2))
