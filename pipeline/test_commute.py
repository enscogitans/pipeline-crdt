import pytest

from pipeline import *


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


@pytest.fixture
def init_state():
    app = Applier(PipelineState({}))

    def get_id(name: str) -> BlockId:
        nonlocal app
        res = app.state.get_mapping()
        assert len(res[name]) == 1
        return res[name][0]

    app.apply_local([
        AddBlock("1", "return 1", [], get_timestamp()),
        AddBlock("2", "return 2", [], get_timestamp()),
        AddBlock("3", "return 3", [], get_timestamp()),
        AddBlock("4", "return 4", [], get_timestamp()),
    ])
    app.apply_local([
        AddBlock("5", "return a+b+c", [get_id("1"), get_id("2"), get_id("3")], get_timestamp()),
        AddBlock("6", "return a+b", [get_id("3"), get_id("4")], get_timestamp()),
        AddBlock("7", "return a", [get_id("4")], get_timestamp()),
    ])
    app.apply_local([
        AddBlock("8", "return a", [get_id("5")], get_timestamp()),
        AddBlock("9", "return a+b", [get_id("6"), get_id("7")], get_timestamp()),
    ])
    app.apply_local([
        AddBlock("10", "return a", [get_id("8")], get_timestamp()),
    ])
    app.apply_local([
        DeleteBlock(get_id("9")),
        DeleteBlock(get_id("7")),
    ])
    return app.state


def test_add_add(init_state: PipelineState):
    app_1 = Applier(init_state)
    app_2 = Applier(init_state)
    id_5, = init_state.get_mapping()["5"]
    id_6, = init_state.get_mapping()["6"]
    id_10, = init_state.get_mapping()["10"]

    upds_1 = app_1.apply_local([
        AddBlock("100", "hi", [id_5, id_6], get_timestamp()),
    ])
    upds_2 = app_2.apply_local([
        AddBlock("101", "hello", [id_10], get_timestamp()),
    ])

    assert app_1.state != app_2.state
    app_1.apply_remote(upds_2)
    app_2.apply_remote(upds_1)
    assert app_1.state == app_2.state

    id_100, = app_1.state.get_mapping()["100"]
    id_101, = app_1.state.get_mapping()["101"]
    assert id_100 in app_1.state.blocks[id_5].outputs
    assert id_100 in app_1.state.blocks[id_6].outputs
    assert id_101 in app_1.state.blocks[id_10].outputs


def test_add_del(init_state: PipelineState):
    app_1 = Applier(init_state)
    app_2 = Applier(init_state)
    id_5, = init_state.get_mapping()["5"]
    id_6, = init_state.get_mapping()["6"]

    upds_1 = app_1.apply_local([
        AddBlock("100", "hi", [id_5, id_6], get_timestamp()),
    ])
    upds_2 = app_2.apply_local([
        DeleteBlock(id_6),
    ])

    assert app_1.state != app_2.state
    app_1.apply_remote(upds_2)
    app_2.apply_remote(upds_1)
    assert app_1.state == app_2.state

    id_100, = app_1.state.get_mapping()["100"]

    assert not app_1.state.is_hidden(id_6)
    assert app_1.state.has_block(id_100)
    assert id_100 in app_1.state.blocks[id_5].outputs
    assert id_100 in app_1.state.blocks[id_6].outputs


def test_add_edit(init_state):
    app_1 = Applier(init_state)
    app_2 = Applier(init_state)
    id_2, = init_state.get_mapping()["2"]
    id_3, = init_state.get_mapping()["3"]
    id_4, = init_state.get_mapping()["4"]
    id_5, = init_state.get_mapping()["5"]
    id_6, = init_state.get_mapping()["6"]

    upds_1 = app_1.apply_local([
        AddBlock("100", "hi", [id_5, id_6], get_timestamp()),
    ])
    upds_2 = app_2.apply_local([
        EditBlock(id_6, "hello", [id_2, id_4], get_timestamp()),
    ])

    assert app_1.state != app_2.state
    app_1.apply_remote(upds_2)
    app_2.apply_remote(upds_1)
    assert app_1.state == app_2.state

    id_100, = app_1.state.get_mapping()["100"]
    assert id_100 in app_1.state.blocks[id_5].outputs
    assert id_100 in app_1.state.blocks[id_6].outputs
    assert id_3 not in app_1.state.blocks[id_6].inputs


def test_del_del(init_state):
    app_1 = Applier(init_state)
    app_2 = Applier(init_state)
    id_6, = init_state.get_mapping()["6"]
    id_10, = init_state.get_mapping()["10"]

    upds_1 = app_1.apply_local([
        DeleteBlock(id_6),
    ])
    upds_2 = app_2.apply_local([
        DeleteBlock(id_10),
    ])

    assert app_1.state != app_2.state
    app_1.apply_remote(upds_2)
    app_2.apply_remote(upds_1)
    assert app_1.state == app_2.state

    assert app_1.state.is_hidden(id_6)
    assert app_1.state.is_hidden(id_10)


def test_del_edit_1(init_state):
    app_1 = Applier(init_state)
    app_2 = Applier(init_state)
    id_5, = init_state.get_mapping()["5"]
    id_6, = init_state.get_mapping()["6"]
    id_8, = init_state.get_mapping()["8"]

    assert id_6 not in init_state.blocks[id_8].inputs
    upds_1 = app_1.apply_local([
        DeleteBlock(id_6),
    ])
    upds_2 = app_2.apply_local([
        EditBlock(id_8, "hello world", [id_5, id_6], get_timestamp()),
    ])

    assert app_1.state != app_2.state
    app_1.apply_remote(upds_2)
    app_2.apply_remote(upds_1)
    assert app_1.state == app_2.state

    assert not app_1.state.is_hidden(id_6)


def test_del_edit_2(init_state):
    app_1 = Applier(init_state)
    app_2 = Applier(init_state)
    id_3, = init_state.get_mapping()["3"]
    id_4, = init_state.get_mapping()["4"]
    id_6, = init_state.get_mapping()["6"]

    upds_1 = app_1.apply_local([
        DeleteBlock(id_6),
    ])
    upds_2 = app_2.apply_local([
        EditBlock(id_6, "hello world", [id_3, id_4], get_timestamp()),
    ])

    assert app_1.state != app_2.state
    app_1.apply_remote(upds_2)
    app_2.apply_remote(upds_1)
    assert app_1.state == app_2.state

    assert app_1.state.is_hidden(id_6)


def test_edit_edit(init_state):
    app_1 = Applier(init_state)
    app_2 = Applier(init_state)
    id_4, = init_state.get_mapping()["4"]
    id_6, = init_state.get_mapping()["6"]
    id_8, = init_state.get_mapping()["8"]
    id_10, = init_state.get_mapping()["10"]

    upds_1 = app_1.apply_local([
        EditBlock(id_10, "hello", [id_8, id_6], get_timestamp()),
    ])
    upds_2 = app_2.apply_local([
        EditBlock(id_10, "Hello world!", [id_8, id_4], get_timestamp()),  # this is the latest update (see timestamp)
    ])

    assert app_1.state != app_2.state
    app_1.apply_remote(upds_2)
    app_2.apply_remote(upds_1)
    assert app_1.state == app_2.state

    assert app_1.state.blocks[id_10].code == "Hello world!"
    assert app_1.state.blocks[id_10].inputs == [id_8, id_4]
