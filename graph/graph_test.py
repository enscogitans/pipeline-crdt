import graph


def test_add_node():
    state = graph.GraphState()
    assert not state.has_node(1)
    upd = graph.AddNode(1)
    upd.prepare(state)
    upd.effect(state)
    assert state.has_node(1)


def test_erase_node():
    state = graph.GraphState(node_keys=[1])
    assert state.has_node(1)
    upd = graph.EraseNode(1)
    upd.prepare(state)
    upd.effect(state)
    assert not state.has_node(1)


def test_add_edge():
    state = graph.GraphState(node_keys=[1, 2])
    assert not state.has_edge(1, 2)
    upd = graph.AddEdge(1, 2)
    upd.prepare(state)
    upd.effect(state)
    assert state.has_edge(1, 2)


def test_erase_edge():
    state = graph.GraphState(node_keys=[1, 2], edges_keys=[(1, 2)])
    assert state.has_edge(1, 2)
    upd = graph.EraseEdge(1, 2)
    upd.prepare(state)
    upd.effect(state)
    assert not state.has_edge(1, 2)
