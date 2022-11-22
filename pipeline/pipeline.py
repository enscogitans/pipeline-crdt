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
    is_hidden: bool = False


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

    def is_hidden(self, block_id: BlockId) -> bool:
        return self.blocks[block_id].is_hidden

    def hide(self, block_id: BlockId) -> None:
        assert all(self.is_hidden(child_id) for child_id in self.blocks[block_id].outputs)
        self.blocks[block_id].is_hidden = True

    def unhide(self, block_id: BlockId) -> None:
        self.blocks[block_id].is_hidden = False
        for parent_id in self.blocks[block_id].inputs:
            if self.is_hidden(parent_id):
                self.unhide(parent_id)


class Update(abc.ABC):
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
        assert all(not state.is_hidden(block_id) for block_id in self._inputs)
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
        for parent_id in self._block.inputs:
            if state.is_hidden(parent_id):
                state.unhide(parent_id)
            state.blocks[parent_id].outputs.add(self._block.id)
        state.blocks[self._block.id] = deepcopy(self._block)


class DeleteBlock(Update):
    def __init__(self, block_id: BlockId):
        super().__init__()
        self._block_id = block_id

    def prepare(self, state: PipelineState) -> None:
        assert state.has_block(self._block_id)
        assert not state.is_hidden(self._block_id)
        assert all(state.is_hidden(child_id) for child_id in state.blocks[self._block_id].outputs)

    def effect(self, state: PipelineState) -> None:
        if state.is_hidden(self._block_id):
            return
        if any(not state.is_hidden(child_id) for child_id in state.blocks[self._block_id].outputs):
            return
        state.hide(self._block_id)


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
        assert not state.is_hidden(self._block_id)

    def effect(self, state: PipelineState) -> None:
        block = state.blocks[self._block_id]
        if block.last_edit_ts > self._ts:
            return
        block.last_edit_ts = self._ts
        block.code = self._new_code
        for old_parent_id in block.inputs:
            state.blocks[old_parent_id].outputs.remove(self._block_id)
        for new_parent_id in self._new_inputs:
            if not block.is_hidden and state.is_hidden(new_parent_id):
                state.unhide(new_parent_id)
            state.blocks[new_parent_id].outputs.add(self._block_id)
        state.blocks[self._block_id].inputs = self._new_inputs
