from pathlib import Path

from yaml_diff_v3.service import Service


def run_case(case_no: int):
    resources_dir = Path(__file__).parent / f"case_{case_no}"
    with open(resources_dir / "v0.yaml") as f:
        base_text = f.read()
    with open(resources_dir / "v1.yaml") as f:
        modified_text = f.read()

    service = Service()
    merged_text = service.merge_with_empty_graph(base_text, base_text, modified_text)
    with open(resources_dir / "merged.yaml", "w") as f:
        print(end=merged_text, file=f)

    assert modified_text == merged_text


def main():
    run_case(1)
    run_case(2)
    run_case(3)


if __name__ == "__main__":
    main()
