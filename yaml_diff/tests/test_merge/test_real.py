from yaml_diff.graph import merge_yaml
from yaml_diff.utils import load_yaml, assert_yaml_eq, dump_yaml


def test_files():
    yaml_base = load_yaml("trial_0.yml")
    yaml_v1 = load_yaml("trial_1.yml")
    yaml_v2 = load_yaml("trial_2.yml")
    expected = load_yaml("expected.yml")

    merged = merge_yaml(yaml_base, yaml_v1, "id_1", 1, yaml_v2, "id_2", 2)
    dump_yaml(merged, "merged.yml")
    assert_yaml_eq(expected, merged)
