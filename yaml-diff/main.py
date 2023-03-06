import yaml

from pipeline.pipeline import *


def get_loader():
    # To parse anchors see https://stackoverflow.com/questions/37413345/yaml-anchors-definitions-loading-in-pyyaml
    def unknown(loader, suffix, node):
        if isinstance(node, yaml.ScalarNode):
            constructor = loader.__class__.construct_scalar
        elif isinstance(node, yaml.SequenceNode):
            constructor = loader.__class__.construct_sequence
        else:
            assert isinstance(node, yaml.MappingNode)
            constructor = loader.__class__.construct_mapping
        data = constructor(loader, node)
        if isinstance(node, yaml.MappingNode):
            data["__tag"] = suffix  # just for me if I want to use it somehow
        return data

    yaml.add_multi_constructor('!', unknown)  # TODO: do not update global loader
    # yaml.add_multi_constructor('tag:', unknown)
    return yaml.Loader


def read_config(filename: str) -> dict:
    with open(filename) as f:
        config = yaml.load(f, Loader=get_loader())
    return {"pipeline": config["pipeline"]}


def save_config(pipeline: dict, filename: str):
    with open(filename, "w") as f:
        yaml.dump(pipeline, f, yaml.Dumper, default_flow_style=False, default_style=None)


def stage_to_block(stage):
    id_ = stage["name"]  # TODO: maybe some unique id?
    name = stage["name"]
    inputs = stage.get("depends_on", [])  # Should use ids here, not names

    code = stage.copy()
    code.pop("name")
    code.pop("depends_on", None)
    return Block(id=id_, name=name, code=code, inputs=inputs,
                 outputs=set(), last_edit_ts=Timestamp(0))  # TODO: get timestamp


def config_to_pipeline_state(config):
    blocks = {}
    for stage in config["pipeline"]["runs"]:
        block = stage_to_block(stage)
        blocks[block.id] = block
    for block in blocks.values():
        for parent_id in block.inputs:
            blocks[parent_id].outputs.add(block.id)
    return PipelineState(blocks)


def make_add(diff):
    block_info = stage_to_block(diff["value"])  # this dict would have all stage's fields
    return AddBlock(
        name=block_info.name,
        code=block_info.code,
        inputs=block_info.inputs,
        ts=Timestamp(1),  # TODO: set correct ts
    )


def make_del(G, diff):
    path = diff["path"].split("/")
    assert path[0] == ""
    node = G
    for elem in path[1:]:
        try:
            elem = int(elem)
        except:
            pass
        node = node[elem]
    block = stage_to_block(node)
    return DeleteBlock(block.id)


def make_update(G, diff):
    if diff["op"] == "add":
        return make_add(diff)
    assert diff["op"] == "remove"
    return make_del(G, diff)


def make_updates(G, diffs):
    return [make_update(G, diff) for diff in diffs]


class Applier:
    def __init__(self, state: PipelineState):
        self.state = state.copy()

    def apply_local(self, upds: List[Update]) -> List[Update]:
        upds = [deepcopy(upd) for upd in upds]
        for upd in upds:
            upd.prepare(self.state)
            upd.effect(self.state)
        return upds

    def apply_remote(self, upds: List[Update]) -> None:
        for upd in upds:
            upd.effect(self.state)


def main():
    G0 = read_config("trial_0.yml")
    # G1 = read_config("trial_1.yml")
    # G2 = read_config("trial_2.yml")
    # with open("G0.json", "w") as f:
    #     json.dump(G0, f, ensure_ascii=False, indent=2)
    # with open("G1.json", "w") as f:
    #     json.dump(G1, f, ensure_ascii=False, indent=2)
    # with open("G2.json", "w") as f:
    #     json.dump(G2, f, ensure_ascii=False, indent=2)

    # https://extendsclass.com/json-patch.html
    diff_01 = [
        {"op": "remove", "path": "/pipeline/runs/3"},
    ]
    diff_02 = [
        {
            "op": "add",
            "path": "/pipeline/runs/4",
            "value": {
                "name": "graph_usage",
                "depends_on": [
                    "draw_graphs"
                ],
                "script": [
                    "echo \"Use notebook results\""
                ],
                "__tag": "BasicStage"
            }
        }
    ]

    P0 = config_to_pipeline_state(G0)
    # P1 = config_to_pipeline_state(G1)
    # P2 = config_to_pipeline_state(G2)

    upds_1 = make_updates(G0, diff_01)
    upds_2 = make_updates(G0, diff_02)

    app_1 = Applier(P0)
    app_2 = Applier(P0)

    remote_updates_1 = app_1.apply_local(upds_1)
    remote_updates_2 = app_2.apply_local(upds_2)
    app_1.apply_remote(remote_updates_2)
    app_2.apply_remote(remote_updates_1)
    assert app_1.state == app_2.state

    # TODO: dump state to yaml config file


if __name__ == "__main__":
    main()
