from yaml_diff.graph import merge_yaml
from yaml_diff.utils import load_yaml, dump_yaml


def main(yaml_base_path, yaml_v1_path, yaml_v2_path, result_path):
    yaml_base = load_yaml(yaml_base_path)
    yaml_v1 = load_yaml(yaml_v1_path)
    yaml_v2 = load_yaml(yaml_v2_path)

    yaml_merged = merge_yaml(yaml_base, yaml_v1, "id_1", 1, yaml_v2, "id_2", 2)
    dump_yaml(yaml_merged, result_path)


if __name__ == "__main__":
    yaml_base_path = "trial_0.yml"
    yaml_v1_path = "trial_1.yml"  # В пайплайне удалён draw_graphs
    yaml_v2_path = "trial_2.yml"  # В пайплайн добавлен graph_usage
    result_path = "trial_merged.yml"

    main(yaml_base_path, yaml_v1_path, yaml_v2_path, result_path)
    print(load_yaml(result_path))