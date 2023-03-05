import abc
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, NewType, Optional, Set, TypeAlias
from uuid import uuid4

BlockId = NewType("BlockId", str)
Code: TypeAlias = str
Timestamp = NewType("Timestamp", int)


_last_id = 0
def make_unique_id() -> BlockId:
    global _last_id
    _last_id += 1
    return BlockId(f"id{_last_id}")
    # return BlockId(str(uuid4()))


_counter = 0
def get_timestamp() -> Timestamp:
    global _counter
    _counter += 1
    return Timestamp(_counter)


@dataclass
class Block:
    id: BlockId
    name: str
    code: Code
    inputs: List[BlockId]
    outputs: Set[BlockId]
    last_edit_ts: Timestamp
    is_deprecated: bool = False
    # is_hidden: bool = False
    is_all_children_hidden: bool = True

    @property
    def is_hidden(self) -> bool:
        return self.is_deprecated and self.is_all_children_hidden


@dataclass
class PipelineState:
    blocks: Dict[BlockId, Block]

    def copy(self) -> "PipelineState":
        return deepcopy(self)

    def get_mapping(self) -> Dict[str, List[BlockId]]:
        """name -> block_ids"""
        res = defaultdict(list)
        for block in self.blocks.values():
            res[block.name].append(block.id)
        return dict(res)

    def has_block(self, block_id: BlockId) -> bool:
        return block_id in self.blocks

    def is_deprecated(self, block_id: BlockId) -> bool:
        return self.blocks[block_id].is_deprecated

    def update_is_all_children_hidden(self, block_id: BlockId) -> None:
        block = self.blocks[block_id]
        prev_val = block.is_all_children_hidden
        block.is_all_children_hidden = all(self.blocks[out_id].is_hidden for out_id in block.outputs)
        if block.is_all_children_hidden == prev_val:
            return
        for parent_id in block.inputs:
            self.update_is_all_children_hidden(parent_id)

    def is_hidden(self, block_id: BlockId) -> bool:
        return self.blocks[block_id].is_hidden

    # def hide(self, block_id: BlockId) -> None:
    #     assert all(self.is_hidden(child_id) for child_id in self.blocks[block_id].outputs)
    #     self.blocks[block_id].is_hidden = True

    def deprecate(self, block_id: BlockId) -> None:
        self.blocks[block_id].is_deprecated = True

    # def unhide(self, block_id: BlockId) -> None:
    #     self.blocks[block_id].is_hidden = False
    #     for parent_id in self.blocks[block_id].inputs:
    #         if self.is_hidden(parent_id):
    #             self.unhide(parent_id)


class Update(abc.ABC):
    def __init__(self):
        self.id = uuid4()

    @abc.abstractmethod
    def prepare(self, state: PipelineState) -> None:
        """Executes only on local machine, before pushing operation to the server. Must not change state"""

    @abc.abstractmethod
    def effect(self, state: PipelineState) -> None:
        """Changes state"""


class AddBlock(Update):
    def __init__(self, name: str, code: Code, inputs: List[BlockId], ts: Timestamp):
        super().__init__()
        self._name = name
        self._code = code
        self._inputs = inputs
        self._ts = ts
        self._block: Optional[Block] = None

    def prepare(self, state: PipelineState) -> None:
        assert all(state.has_block(block_id) for block_id in self._inputs)
        assert all(not state.is_deprecated(block_id) for block_id in self._inputs)
        self._block = Block(
            name=self._name,
            id=make_unique_id(),
            inputs=self._inputs,
            outputs=set(),
            code=self._code,
            last_edit_ts=self._ts,
        )

    def effect(self, state: PipelineState) -> None:
        assert self._block is not None
        state.blocks[self._block.id] = deepcopy(self._block)
        for parent_id in self._block.inputs:
            state.blocks[parent_id].outputs.add(self._block.id)
            state.update_is_all_children_hidden(parent_id)


class DeleteBlock(Update):
    def __init__(self, block_id: BlockId):
        super().__init__()
        self._block_id = block_id

    def prepare(self, state: PipelineState) -> None:
        assert state.has_block(self._block_id)
        assert not state.is_deprecated(self._block_id)
        assert all(state.is_deprecated(child_id) for child_id in state.blocks[self._block_id].outputs)

    def effect(self, state: PipelineState) -> None:
        if state.is_deprecated(self._block_id):
            return
        state.deprecate(self._block_id)
        for parent_id in state.blocks[self._block_id].inputs:
            state.update_is_all_children_hidden(parent_id)


class EditBlock(Update):
    def __init__(self, block_id: BlockId, new_code: Code, new_inputs: List[BlockId], ts: Timestamp):
        # TODO: maybe allow un-hiding
        super().__init__()
        self._block_id = block_id
        self._new_code = new_code
        self._new_inputs = new_inputs
        self._ts = ts

    def prepare(self, state: PipelineState) -> None:
        # TODO: check no loops will occur
        assert not state.is_deprecated(self._block_id)

    def effect(self, state: PipelineState) -> None:
        block = state.blocks[self._block_id]
        if block.last_edit_ts > self._ts:
            return
        block.last_edit_ts = self._ts
        block.code = self._new_code
        for old_parent_id in block.inputs:
            state.blocks[old_parent_id].outputs.remove(self._block_id)
            state.update_is_all_children_hidden(old_parent_id)
        for new_parent_id in self._new_inputs:
            state.blocks[new_parent_id].outputs.add(self._block_id)
            state.update_is_all_children_hidden(new_parent_id)
        state.blocks[self._block_id].inputs = self._new_inputs
