import itertools
import random

from matplotlib import pyplot as plt

random.seed(0xABBA)

import networkx as nx

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
        self.dump_state(None)

    def apply_local(self, upds: List[Update]) -> List[Update]:
        for upd in upds:
            upd.prepare(self.state)
            upd.effect(self.state)
            self.dump_state(upd)
            self.updates_ids.add(upd.id)
            self.updates_list.append(upd)
        return upds

    def apply_remote(self, upds: List[Update]) -> None:
        for upd in upds:
            upd.effect(self.state)
            self.dump_state(upd, is_sync=True)
            self.updates_ids.add(upd.id)
            self.updates_list.append(upd)
        self.dump_state(None)

    def dump_state(self, upd, is_sync=False) -> None:
        if self.idx is None:
            return

        Applier.cnt += 1
        i = Applier.cnt

        if upd is None:
            id_ = None
            add_edges = set()
            del_edges = set()
            text = ""
        elif isinstance(upd, AddBlock):
            id_ = upd._block.id
            add_edges = set(upd._block.inputs)
            del_edges = set()
            text = f"Add {id_}"
        elif isinstance(upd, EditBlock):
            id_ = upd._block_id
            prev_inputs = set(self.state.blocks[id_].inputs)
            curr_inputs = set(upd._new_inputs)
            # prev и curr должны почти совпадать, так что это бессмысленно
            add_edges = curr_inputs - prev_inputs
            del_edges = prev_inputs - curr_inputs
            if del_edges:
                print(add_edges, del_edges)
            text = f"Edit {id_}"
        else:
            assert isinstance(upd, DeleteBlock)
            id_ = upd._block_id
            add_edges = set()
            del_edges = set()
            text = f"Delete {id_}"
        if id_ is not None:
            add_edges2 = {(u, id_) for u in add_edges}
            del_edges2 = {(u, id_) for u in del_edges}
            add_edges = add_edges2
            del_edges = del_edges2

        G = nx.DiGraph()
        G.add_nodes_from([block.id for block in self.state.blocks.values() if not block.is_hidden])
        for block in self.state.blocks.values():
            if block.is_hidden:
                continue
            for nxt_id in block.outputs:
                if not self.state.is_hidden(nxt_id):
                    G.add_edge(block.id, nxt_id)

        def get_color(node):
            if node == id_:
                return 'blue'
            if self.state.is_deprecated(node):
                return 'grey'
            return 'black'

        def get_edge_color(edge):
            # if edge in add_edges:
            #     return "green"
            # if edge in del_edges:
            #     return "red"
            return "black"

        colors = [get_color(node) for node in G.nodes]
        edge_color = [get_edge_color(edge) for edge in G.edges]

        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
        fig, ax = plt.subplots(1, 1, figsize=(6, 9))
        nx.draw(G, pos, with_labels=True, node_size=900, node_color=colors,
                edge_color=edge_color, width=2.0,
                font_color='white', ax=ax)
        if is_sync:
            fig.set_facecolor('xkcd:salmon')
        ax.set_title(text)
        name = f"{i}".zfill(4)
        fig.savefig(f'{self.idx}/{name}.png')
        plt.close(fig)


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


def make_random_operation(state: PipelineState) -> Optional[Update]:
    if random.randint(0, 4) == 0:
        return None  # Means sync

    visible_blocks = [block for name, block in state.blocks.items() if not block.is_deprecated]
    deletable_blocks = [
        block for block in visible_blocks if all(state.is_deprecated(out) for out in block.outputs)
    ]

    op_idx = random.randint(0, 100)
    if op_idx <= 15 and deletable_blocks:  # Del
        block = random.choice(deletable_blocks)
        return DeleteBlock(block.id)

    if op_idx <= 70 and visible_blocks:  # Edit
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
    for i in range(2, 6):
        prev_id = get_id(name)
        name = make_unique_name()
        code = f"return '{name}'"
        app.apply_local([AddBlock(name, code, [prev_id], get_timestamp())])
    return app.state


import shutil
import os
def main():
    shutil.rmtree("./1")
    shutil.rmtree("./2")
    shutil.rmtree("./3")
    shutil.rmtree("./4")
    os.mkdir("./1")
    os.mkdir("./2")
    os.mkdir("./3")
    os.mkdir("./4")

    st = init_state()
    Applier.cnt = 0
    apps = [Applier(st, i + 1) for i in range(4)]
    pulled_cnt = [[0 for _ in apps] for _ in apps]

    for _ in range(6):
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
        app.dump_state(None)

    assert apps[0].state != init_state
    for i in range(1, len(apps)):
        assert apps[i - 1].updates_ids == apps[i].updates_ids
        assert apps[i - 1].state == apps[i].state


if __name__ == "__main__":
    main()
