import pickle
from copy import deepcopy

from yaml_diff_v3.crdt_graph import Timestamp, SessionId
from yaml_diff_v3.service import Service


def main(i: int):
    with open(f"merged/{i - 1}.yaml") as f:
        base_text = f.read()

    service = Service()
    if i == 1:
        graph = service.make_initial_crdt_graph(base_text, Timestamp(3 * i))
    else:
        with open(f"merged/{i - 1}.pickle", "rb") as f:
            graph = pickle.load(f)

    with open(f"user_1/{i}.yaml") as f:
        text_1 = f.read()
        updates_1 = service.build_local_updates(graph, base_text, text_1,
                                                SessionId(f"{3 * i + 1}"),
                                                Timestamp(3 * i + 1))
    with open(f"user_2/{i}.yaml") as f:
        text_2 = f.read()
        updates_2 = service.build_local_updates(graph, base_text, text_2,
                                                SessionId(f"{3 * i + 2}"),
                                                Timestamp(3 * i + 2))

    # with open(f"merged/{i-1}_1.upds", "wb") as f:
    #     pickle.dump(updates_1, f)
    # with open(f"merged/{i-1}_2.upds", "wb") as f:
    #     pickle.dump(updates_2, f)

    graph_1 = service.apply_updates(deepcopy(graph), updates_1 + updates_2, set())
    res_yaml_1 = service.convert_to_yaml(graph_1)

    graph_2 = service.apply_updates(deepcopy(graph), updates_2 + updates_1, set())
    res_yaml_2 = service.convert_to_yaml(graph_2)

    print(res_yaml_1)
    print(res_yaml_2)
    assert res_yaml_1 == res_yaml_2
    with open(f"merged/{i}.pickle", "wb") as f:
        pickle.dump(graph_1, f)
    with open(f"merged/{i}.yaml", "w") as f:
        print(res_yaml_1, end="", file=f)


if __name__ == "__main__":
    i = 2
    main(i)
