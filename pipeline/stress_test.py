import itertools
import random
random.seed(0xABBA)

import pytest

from pipeline import *


_last_int = 0
def make_unique_name() -> str:
    global _last_int
    _last_int += 1
    return f"{_last_int}"


class Applier:
    cnt = 0

    def __init__(self, state: PipelineState, idx=None):
        self.state = state.copy()
        self.updates_ids = set()
        self.updates_list = []
        self.log = []
        self.idx = idx

    def apply_local(self, upds: List[Update]) -> List[Update]:
        for upd in upds:
            upd.prepare(self.state)
            upd.effect(self.state)
            self.updates_ids.add(upd.id)
            self.updates_list.append(upd)
        return upds

    def apply_remote(self, upds: List[Update]) -> None:
        for upd in upds:
            upd.effect(self.state)
            self.updates_ids.add(upd.id)
            self.updates_list.append(upd)


def get_all_reachable_ids(state: PipelineState, block_id: BlockId) -> Set[BlockId]:
    used = set()
    queue = [block_id]
    i = 0
    while i < len(queue):
        next_block_id = queue[i]
        i += 1
        if next_block_id in used:
            continue
        used.add(next_block_id)
        queue += list(state.blocks[next_block_id].outputs)
    return used


def check_cycles(state: PipelineState):
    used = set()
    finished = set()
    log = []

    def dfs(block_id):
        nonlocal used, finished, log
        used.add(block_id)
        for next_id in state.blocks[block_id].outputs:
            if next_id not in used:
                if dfs(next_id):
                    log.append(next_id)
                    return True
            elif next_id in used and next_id not in finished:
                log.append(next_id)
                return True
        finished.add(block_id)
        return False

    for block_id in state.blocks:
        if block_id not in used and dfs(block_id):
            return log
    return log


def make_random_operation(state: PipelineState) -> Optional[Update]:
    if random.randint(0, 4) == 0:
        return None  # Means sync

    visible_blocks = [block for name, block in state.blocks.items() if not block.is_deprecated]
    deletable_blocks = [
        block for block in visible_blocks if all(state.is_deprecated(out) for out in block.outputs)
    ]

    op_idx = random.randint(0, 100)
    if op_idx <= 40 and deletable_blocks:  # Del
        block = random.choice(deletable_blocks)
        return DeleteBlock(block.id)

    if op_idx <= 90 and visible_blocks:  # Edit
        block = random.choice(visible_blocks)

        possible_inputs_set = set(block.id for block in visible_blocks) - get_all_reachable_ids(state, block.id)
        # assert all(inp_id in possible_inputs_set for inp_id in block.inputs), "Cycles?"
        # assert len(possible_inputs_set) >= len(block.inputs)
        possible_inputs_set |= set(block.inputs)
        if not possible_inputs_set:
            new_inputs_cnt = 0
        else:
            new_inputs_cnt = random.randint(1, min(3, len(possible_inputs_set)))
        new_inputs = random.sample(sorted(list(possible_inputs_set)), new_inputs_cnt)
        # new_inputs = block.inputs
        return EditBlock(block.id, block.code + ";", new_inputs, get_timestamp())

    assert op_idx <= 100  # Add
    if not visible_blocks:
        prev_cnt = 0
    else:
        prev_cnt = random.randint(1, min(3, len(visible_blocks)))
    prev_blocks = random.sample(visible_blocks, prev_cnt)
    name = make_unique_name()
    return AddBlock(name, f"return '{name}'", [block.id for block in prev_blocks], get_timestamp())


@pytest.fixture
def init_state():
    Applier.cnt = 0
    app = Applier(PipelineState({}))

    def get_id(name: str) -> BlockId:
        nonlocal app
        res = app.state.get_mapping()
        assert len(res[name]) == 1
        return res[name][0]

    name = make_unique_name()
    app.apply_local([AddBlock(name, f"return '{name}'", [], get_timestamp())])
    for i in range(2, 11):
        prev_id = get_id(name)
        name = make_unique_name()
        code = f"return '{name}'"
        app.apply_local([AddBlock(name, code, [prev_id], get_timestamp())])
    return app.state


# @pytest.mark.skip
def test_stress(init_state):
    app_1 = Applier(init_state)
    local_upds_1 = []
    pulled_cnt_1 = 0

    app_2 = Applier(init_state)
    local_upds_2 = []
    pulled_cnt_2 = 0

    for _ in range(1000):
        upd_1 = make_random_operation(app_1.state)
        if upd_1 is None:
            pulled_upds = local_upds_2[pulled_cnt_1:]
            pulled_cnt_1 += len(pulled_upds)
            # print(len(pulled_upds))
            app_1.apply_remote(pulled_upds)
        else:
            local_upds_1.append(upd_1)
            app_1.apply_local([upd_1])

        upd_2 = make_random_operation(app_2.state)
        if upd_2 is None:
            pulled_upds = local_upds_1[pulled_cnt_2:]
            pulled_cnt_2 += len(pulled_upds)
            app_2.apply_remote(pulled_upds)
        else:
            local_upds_2.append(upd_2)
            app_2.apply_local([upd_2])

        # assert not check_cycles(app_1.state), "App1"
        # assert not check_cycles(app_2.state), "App2"

    pulled_upds = local_upds_2[pulled_cnt_1:]
    pulled_cnt_1 += len(pulled_upds)
    app_1.apply_remote(pulled_upds)

    pulled_upds = local_upds_1[pulled_cnt_2:]
    pulled_cnt_2 += len(pulled_upds)
    app_2.apply_remote(pulled_upds)

    assert app_1.state == app_2.state


def test_stress_3(init_state):
    apps = [Applier(init_state, i+1) for i in range(4)]
    pulled_cnt = [[0 for _ in apps] for _ in apps]

    for _ in range(30):
        pairs = list(enumerate(apps))
        random.shuffle(pairs)
        for i, app in pairs:
            upd = make_random_operation(app.state)
            if upd is not None:
                app.apply_local([upd])
            else:
                # sync
                for src_idx in itertools.chain(range(0, i), range(i + 1, len(apps))):
                    start_upd_idx = pulled_cnt[i][src_idx]
                    pulled_cnt[i][src_idx] = len(apps[src_idx].updates_list)
                    app.apply_remote([upd for upd in apps[src_idx].updates_list[start_upd_idx:]
                                      if upd.id not in app.updates_ids])

    # sync all
    for i, app in enumerate(apps):
        for src_idx in itertools.chain(range(0, i), range(i + 1, len(apps))):
            start_upd_idx = pulled_cnt[i][src_idx]
            pulled_cnt[i][src_idx] = len(apps[src_idx].updates_list)
            app.apply_remote([upd for upd in apps[src_idx].updates_list[start_upd_idx:]
                              if upd.id not in app.updates_ids])

    assert apps[0].state != init_state
    for i in range(1, len(apps)):
        assert apps[i - 1].updates_ids == apps[i].updates_ids
        assert apps[i - 1].state == apps[i].state
